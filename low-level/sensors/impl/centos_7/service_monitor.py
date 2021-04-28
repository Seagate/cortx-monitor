# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

"""
 ****************************************************************************
  Description:  Monitors Systemd for service events and notifies
                the ServiceMsgHandler.
 ****************************************************************************
"""

import time
import socket
import copy
import os

from dbus import Interface, SystemBus, DBusException, PROPERTIES_IFACE
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

from zope.interface import implementer
from sensors.ISystem_monitor import ISystemMonitor
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from message_handlers.service_msg_handler import ServiceMsgHandler
from framework.utils.service_logging import logger
from framework.base.sspl_constants import DATA_PATH

from framework.utils.conf_utils import (GLOBAL_CONF, CLUSTER, SRVNODE, SITE_ID,
                RACK_ID, NODE_ID, SSPL_CONF, CLUSTER_ID, Conf)
from framework.utils.severity_reader import SeverityReader
from framework.utils.mon_utils import get_alert_id
from framework.utils.iem import Iem
from framework.base.module_thread import ThreadException
from framework.utils.store_factory import file_store

# Override default store
store = file_store

@implementer(ISystemMonitor)
class ServiceMonitor(SensorThread, InternalMsgQ):
    """ Sensor to monitor state change events of services. """

    SENSOR_NAME       = "ServiceMonitor"
    PRIORITY          = 2

    # Section and keys in configuration file
    SERVICEMONITOR     = SENSOR_NAME.upper()
    RESOURCE_TYPE      = "node:sw:os:service"
    MONITORED_SERVICES = 'monitored_services'
    THREAD_SLEEP       = 'thread_sleep'
    POLLING_FREQUENCY  = 'polling_frequency'
    MAX_WAIT_TIME      = 'threshold_inactive_time'

    CACHE_DIR_NAME  = "server"

    # Dependency list
    DEPENDENCIES = {"plugins": ["SeviceMsgHandler"]}

    @staticmethod
    def name():
        """@return: name of the module."""
        return ServiceMonitor.SENSOR_NAME

    def __init__(self):
        """Initialize the relavent datastructures."""
        super(ServiceMonitor, self).__init__(self.SENSOR_NAME,
                                                self.PRIORITY)

        self.services_to_monitor = copy.deepcopy(
            Conf.get(SSPL_CONF, f"{self.SERVICEMONITOR}>{self.MONITORED_SERVICES}", [])
        )

        self.not_active_services = {
            # 'service_name' : [timestamp, prev_state, prev_substate],
            # timestamp => instance when transition to non_active state occurred.
            # prev_state => state from which it came to non_active state
            # prev_substate => substate from which it came to non_acitve substate.
        }
        self.failed_services = []

        self.service_status = {}

        self.thread_sleep = \
            int(Conf.get(SSPL_CONF, f"{self.SERVICEMONITOR}>{self.THREAD_SLEEP}", 1))

        self.polling_frequency = \
            int(Conf.get(SSPL_CONF, f"{self.SERVICEMONITOR}>{self.POLLING_FREQUENCY}", 30))

        self.max_wait_time = \
            int(Conf.get(SSPL_CONF, f"{self.SERVICEMONITOR}>{self.MAX_WAIT_TIME}", 60))

    def read_data(self):
        """Return the dict of service status."""
        return self.service_status

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues."""
        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(ServiceMonitor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(ServiceMonitor, self).initialize_msgQ(msgQlist)

        self.iem = Iem()
        self.iem.check_exsisting_fault_iems()
        self.KAFKA = self.iem.EVENT_CODE["KAFKA_ACTIVE"][1]

        # Integrate into the main dbus loop to catch events
        DBusGMainLoop(set_as_default=True)

        # Initialize SystemBus and get Manager Interface
        self._bus = SystemBus()
        systemd = self._bus.get_object("org.freedesktop.systemd1",
                                       "/org/freedesktop/systemd1")
        self._manager = Interface(systemd,
                            dbus_interface='org.freedesktop.systemd1.Manager')

        self._site_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{SITE_ID}",'DC01')
        self._rack_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{RACK_ID}",'RC01')
        self._node_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{NODE_ID}",'SN01')
        self._cluster_id = Conf.get(GLOBAL_CONF, f'{CLUSTER}>{CLUSTER_ID}','CC01')

        cache_dir_path = os.path.join(DATA_PATH, self.CACHE_DIR_NAME)
        self.SERVICE_MONITOR_DATA_PATH = os.path.join(cache_dir_path,
                                         f'SERVICE_MONITOR_DATA_{self._node_id}')
        # Get the stored previous service info
        self.persistent_service_data = {}
        if os.path.isfile(self.SERVICE_MONITOR_DATA_PATH):
            self.persistent_service_data = \
                store.get(self.SERVICE_MONITOR_DATA_PATH)
        if self.persistent_service_data:
            self.not_active_services = \
                self.persistent_service_data['not_active_services']
            self.failed_services = \
                self.persistent_service_data['failed_services']
            self.service_status = \
                self.persistent_service_data['service_status']
        else:
            self.persistent_service_data = {
                'not_active_services' : self.not_active_services,
                'failed_services' : self.failed_services,
                'service_status' : self.service_status
            }
            store.put(self.persistent_service_data,
                      self.SERVICE_MONITOR_DATA_PATH)

        self.remove_disabled_services()

        return True

    def remove_disabled_services(self):
        """Remove `disabled` services from the list of services to monitor."""
        temp = copy.deepcopy(self.services_to_monitor)
        for service in temp:
            try:
                if 'disabled' in str(self._manager.GetUnitFileState(service)):
                    self.services_to_monitor.remove(service)
            except DBusException as err:
                # If a service is enabled then it definitely has 'UnitFileState`,
                # but for disabled both presence or absence of UnitFileState is
                # possible. so if `UnitFileState' not present for the service,
                # it is definitely disabled.
                logger.debug(f"{service} is not getting monitored due "\
                             f"to an error : {err}")
                self.services_to_monitor.remove(service)

    def run(self):
        logger.info(f"Monitoring Services : {self.services_to_monitor}")
        try:
            # Register all the services to signal of 'PropertiesChanged' and
            # raise an alert if some service is not active on initially or if
            # Unit is not found for the service
            services_to_monitor_copy = copy.deepcopy(self.services_to_monitor)
            for service in services_to_monitor_copy:
                err = self.connect_to_prop_changed_signal(service)
                if err:
                    self.raise_alert(service, "N/A", "N/A", "N/A", "N/A",
                        "N/A", "N/A", 0)
                    logger.error(f"{service} is not active initially. \n Error {err}")
                else:
                    self.services_to_monitor.remove(service)

            logger.debug(f"failed_services : {self.failed_services}")
            logger.debug(f"services_to_monitor : {self.services_to_monitor}")

            # Retrieve the main loop which will be called in the run method
            self._loop = GLib.MainLoop()

            # Initialize the gobject threads and get its context
            GLib.threads_init()
            context = self._loop.get_context()

            time_to_check_lists = self.current_time() + self.polling_frequency

            # WHILE LOOP FUNCTION : every second we check for
            # properties change event if any generated (using context
            # iteration) and after a delay of polling frequency we
            # check for inactive processes.
            while self.is_running():
                # At interval of 'thread_sleep' check for events occured for
                # registered services and process them(call on_pro_changed())
                context.iteration(False)
                time.sleep(self.thread_sleep)

                # At interval of 'polling_freqency' process unregistered
                # services and services with not-active (intermidiate) state.
                if time_to_check_lists <= self.current_time():
                    time_to_check_lists = self.current_time() + \
                                            self.polling_frequency

                    # Try to bind the enabled services on the node to the
                    # signal whose Unit was earlier not found. On successfully
                    # registering for service state change signal, remove from
                    # local list as monitoring enabled through SystemD
                    # and to avoid re-registration.
                    services_to_monitor_copy = copy.deepcopy(self.services_to_monitor)
                    for service in services_to_monitor_copy:
                        if not self.connect_to_prop_changed_signal(service):
                            self.services_to_monitor.remove(service)

                    # Check for services in intermidiate state(not active)
                    self.check_notactive_services()


            logger.info("ServiceMonitor gracefully breaking out " +\
                                "of dbus Loop, not restarting.")
        except GLib.Error as err:
            raise ThreadException(self.SENSOR_NAME,
                "Ungrecefully breaking out of GLib.MainLoop() with error: %s"
                %err)
        except DBusException as err:
            raise ThreadException(self.SENSOR_NAME,
                "Ungracefully breaking out of dbus loop with error: %s"% err)
        except Exception as err:
            raise ThreadException(self.SENSOR_NAME,
                "Ungracefully breaking out of ServiceMonitor:run() "\
                "with error: %s" % err)

    def current_time(self):
        """Returns the time as integer number in seconds since the epoch in UTC."""
        return int(time.time())

    def get_service_status(self, service = None, unit = None):
        """Returns tuple of unit, service name, state, substate and pid."""
        if not unit:
            unit = self._bus.get_object('org.freedesktop.systemd1',\
                                    self._manager.LoadUnit(service))

        Iunit = Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')

        if not service:
            service = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'Id'))

        state = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'ActiveState'))
        substate = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'SubState'))
        pid = str(Iunit.Get('org.freedesktop.systemd1.Service', 'ExecMainPID'))

        return (unit, service, state, substate, pid)

    def connect_to_prop_changed_signal(self, service):
        """
           Bind the service to a signal('PropertiesChanged').

           Fetch the service unit from systemd and its state, substate,
           pid etc. Bind the service to the sigle which will be triggered
           whenever the service changes it's state/substate. Also raise
           an alert if service is in failed/inactive state.
        """
        try:
            unit, _, state, substate, pid = self.get_service_status(service=service)

            if service in self.service_status:
                prev_state = self.service_status[service]['state']
                prev_substate = self.service_status[service]['substate']
                prev_pid = self.service_status[service]['pid']
            else:
                prev_state = prev_substate = prev_pid  = "N/A"

            self.update_status_local_cache(service, state, substate, pid)

            Iunit2 = Interface(unit,
                            dbus_interface='org.freedesktop.systemd1.Manager')

            Iunit2.connect_to_signal('PropertiesChanged',
                                    lambda a, b, c, p = unit :
                                    self.on_prop_changed(a, b, c, p),
                                    dbus_interface=PROPERTIES_IFACE)

            logger.debug(f"{service}({pid}) state is {state}:{substate}")

            if state in  ["activating", "reloading", "deactivating"]:
                if service not in self.not_active_services:
                    self.not_active_services[service] = \
                                    [self.current_time(), state, substate]
            elif state != "active" and service not in self.failed_services:
                self.raise_alert(service, prev_state, state, prev_substate,
                                 substate, prev_pid, pid, 0)
                if service in self.not_active_services:
                    self.not_active_services.pop(service)
                self.failed_services.append(service)
                logger.error(f"{service} is not active initially. state = {state}:{substate}")
            elif state == "active":
                if service in self.failed_services:
                    self.raise_alert(service, prev_state, state, prev_substate,
                        substate, prev_pid, pid, 2)
                    self.failed_services.remove(service)
                    logger.info(f"{service} returned to good state. state = {state}:{substate}")
                if service in self.not_active_services:
                    self.not_active_services.pop(service)
  
            self.update_persistent_cache()

            return None
        except DBusException as err:
            return err

    def check_notactive_services(self):
        """
           Monitor non-active Services.

           Raise FAULT Alert if any of the not-active services has exceeded
           the threshould time for inactivity.
        """
        not_active_services_copy = copy.deepcopy(self.not_active_services)
        for service, [start_time, prev_state, prev_substate]\
                                 in not_active_services_copy.items():

            if self.current_time() - start_time > self.max_wait_time:
                state = self.service_status[service]["state"]
                substate = self.service_status[service]["substate"]
                pid = self.service_status[service]["pid"]
                self.raise_alert(service, prev_state, state, prev_substate,
                                 substate, pid , pid, 1)
                self.not_active_services.pop(service)
                self.failed_services.append(service)
                self.update_persistent_cache()
                logger.warning(f"{service} in {state}:{substate} for "\
                               f"more than {self.max_wait_time} seconds.")

    def update_status_local_cache(self, service, state, substate, pid):
        self.service_status[service] = {
            "state" : state,
            "substate" : substate,
            "pid" : pid
        }

    def on_prop_changed(self, interface, changed_properties,
                                invalidated_properties, unit):
        """Handler to process the service state change signal."""
        _, service, state, substate, pid = self.get_service_status(unit=unit)

        prev_state = self.service_status[service]["state"]
        prev_substate = self.service_status[service]["substate"]
        prev_pid = self.service_status[service]["pid"]

        logger.debug(f"Event for {service}, properties changed from "\
                     f"{prev_state}:{prev_substate} to {state}:{substate}")

        if prev_state == state:
            return


        logger.info(f"{service} changed state from " + \
                    f"{prev_state}:{prev_substate} to {state}:{substate}")

        self.update_status_local_cache(service, state, substate, pid)

        self.action_per_transition(service, prev_state, state,
                    prev_substate, substate, prev_pid, pid)


    def action_per_transition(self, service, prev_state, state,
                        prev_substate, substate, prev_pid, pid):
        """Take action according to the state change of the service."""
        # alert_info_index : index pointing to alert_info table from
        #               ServiceMonitor:raise_alerts() representing alert
        #               description, type, impact etc. to be sent.
        alert_info_index = -1

        logger.debug(f"ServiceMonitor:action_per_transition for {service} : " + \
            f"({prev_state}:{prev_substate}) -> ({state}:{substate})")

        if prev_state in ["active", "reloading"]:
            if state == "active":
                # reloading -> active
                self.not_active_services.pop(service)
                if service in self.failed_services:
                    self.failed_services.remove(service)
                    alert_info_index = 2
            elif state != "failed":
                # active -> deactivating/inactive/reloading/activating
                # or
                # reloading -> deactivating/inactive/activating
                self.not_active_services[service] = \
                    [self.current_time(), prev_state, prev_substate]
            elif state == "failed":
                # active/reloading -> failed
                if service not in self.failed_services:
                    self.failed_services.append(service)
                    alert_info_index = 0
        elif prev_state == "deactivating":
            if state in ["inactive", "activating"]:
                # deactivating -> inactive/activating
                if service not in self.not_active_services:
                    self.not_active_services[service] = \
                        [self.current_time(), prev_state, prev_substate]
            elif state == "failed":
                # deactivating -> failed
                if service not in self.failed_services:
                    self.failed_services.append(service)
                    alert_info_index = 0
            elif state == "active":
                # deactivating -> active
                if service in self.not_active_services:
                    self.not_active_services.pop(service)
                if service in self.failed_services:
                    self.failed_services.remove(service)
                    alert_info_index = 2
            else:
                alert_info_index = 3
        elif prev_state in ["inactive", "failed"]:
            if state == "activating":
                # inactive/failed -> activating
                if service not in self.not_active_services:
                    self.not_active_services[service] = \
                        [self.current_time(), prev_state, prev_substate]
            elif state == "active":
                # inactive/failed -> active
                if service in self.failed_services:
                    self.failed_services.remove(service)
                    alert_info_index = 2
                if service in self.not_active_services:
                    self.not_active_services.pop(service)
            elif state == "failed":
                # inactive -> failed
                if service not in self.failed_services:
                    self.failed_services.append(service)
                    alert_info_index = 0
            else:
                alert_info_index = 3
        elif prev_state == "activating":
            if service in self.not_active_services:
                self.not_active_services.pop(service)
            if state in ["inactive", "deactivating"]:
                # activating -> inactive/deactivating
                self.failed_services.append(service)
                alert_info_index = 0
            elif state == "active":
                # activating -> active
                if service in self.failed_services:
                    self.failed_services.remove(service)
                    alert_info_index = 2
                else :
                    # its a restart.
                    pass
            elif state == "failed":
                # activating -> failed
                if service not in self.failed_services:
                    self.failed_services.append(service)
                    alert_info_index = 0
            else:
                alert_info_index = 3

        if alert_info_index == 3:
            logger.warning(f"{service} service state transition from "\
                           f"{prev_state} to {state} is not handled.")
        if alert_info_index != -1:
            self.raise_alert(service, prev_state, state,
                prev_substate, substate, prev_pid, pid,
                alert_info_index)

        self.update_persistent_cache()

    def raise_alert(self, service, prev_state, state, prev_substate,
                    substate, prev_pid, pid, alert_info_index):
        """Send the alert to ServiceMsgHandler."""
        # Each alert info contains 4 fields
        # 1.Description | 2.Alert Type | 3.Impact | 4.Recommendation
        alert_info = [
            [f"{service} in {state} state.",                 #index 0
                "fault",
                f"{service} service is unavailable.",
                "Try to restart the service"],
            [f"{service} in a {state} state for more than {self.max_wait_time} seconds.",
                "fault",                                     #index 1
                f"{service} service is unavailable.",
                "Try to restart the service"],
            [f"{service} in {state} state.",
                "fault_resolved",                            #index 2
                f"{service} service is available now.",
                ""],
        ]

        description = alert_info[alert_info_index][0]
        alert_type = alert_info[alert_info_index][1]
        impact = alert_info[alert_info_index][2]
        recommendation = alert_info[alert_info_index][3]

        severity = SeverityReader().map_severity(alert_type)
        epoch_time = str(self.current_time())
        alert_id = get_alert_id(epoch_time)
        host_name = socket.getfqdn()

        info = {
                "site_id": self._site_id,
                "cluster_id": self._cluster_id,
                "rack_id": self._rack_id,
                "node_id": self._node_id,
                "resource_type": self.RESOURCE_TYPE,
                "resource_id": service,
                "event_time": epoch_time,
                "description" : description,
                "impact" : impact,
                "recommendation" : recommendation,
                }

        alert_msg = {
            "sensor_request_type": {
                "service_status_alert": {
                    "host_id": host_name,
                    "severity": severity,
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "info": info,
                    "specific_info" : {
                        "service_name" : service,
                        "previous_state" : prev_state,
                        "state" : state,
                        "previous_substate" : prev_substate,
                        "substate" : substate,
                        "previous_pid" : prev_pid,
                        "pid" : pid,
                    }
                }
            }
        }

        self.raise_iem(service, alert_type)
        self._write_internal_msgQ(ServiceMsgHandler.name(), alert_msg)

    def update_persistent_cache(self):
        self.persistent_service_data = {
            'not_active_services' : self.not_active_services,
            'failed_services' : self.failed_services,
            'service_status' : self.service_status
        }
        store.put(self.persistent_service_data,
                    self.SERVICE_MONITOR_DATA_PATH)

    def raise_iem(self, service, alert_type):
        """Raise iem alert for kafka service."""
        if service == "kafka.service" and alert_type == "fault":
            self.iem.iem_fault("KAFKA_NOT_ACTIVE")
            if (self.KAFKA not in self.iem.fault_iems):
                self.iem.fault_iems.append(self.KAFKA)
        elif (service == "kafka.service" and alert_type == "fault_resolved"
            and self.KAFKA in self.iem.fault_iems):
            self.iem.iem_fault_resolved("KAFKA_ACTIVE")
            self.iem.fault_iems.remove(self.KAFKA)

    def suspend(self):
        """Suspend the module thread. It should be non-blocking."""
        super(ServiceMonitor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking."""
        super(ServiceMonitor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread."""
        super(ServiceMonitor, self).shutdown()
