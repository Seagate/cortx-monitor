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

  Description:       Monitors Centos 7 systemd for service events and notifies
                    the ServiceMsgHandler.
 ****************************************************************************
"""

import time
import socket

from dbus import Interface, SystemBus, DBusException, PROPERTIES_IFACE
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject as gobject

from zope.interface import implementer
from sensors.ISystem_monitor import ISystemMonitor
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from message_handlers.service_msg_handler import ServiceMsgHandler
from framework.utils.service_logging import logger

from framework.utils.conf_utils import (GLOBAL_CONF, CLUSTER, SRVNODE, SITE_ID,
                RACK_ID, NODE_ID, CLUSTER_ID, SSPL_CONF, Conf)
from framework.utils.severity_reader import SeverityReader
from framework.utils.mon_utils import get_alert_id

@implementer(ISystemMonitor)
class ServiceMonitor(SensorThread, InternalMsgQ):
    """Sensor to monitor state change events of services."""

    SENSOR_NAME       = "ServiceMonitor"
    PRIORITY          = 2

    # Section and keys in configuration file
    SERVICEMONITOR     = SENSOR_NAME.upper()
    RESOURCE_TYPE      = "node:sw:os:service"
    MONITORED_SERVICES = 'monitored_services'
    THREAD_SLEEP       = 'thread_sleep'
    POLLING_FREQUENCY  = 'polling_frequency'
    MAX_WAIT_TIME      = 'threshold_inactive_time'

    # Dependency list
    DEPENDENCIES = {"plugins": ["SeviceMsgHandler"]}

    @staticmethod
    def name():
        """@return: name of the module."""
        return ServiceMonitor.SENSOR_NAME

    def __init__(self):
        "Initialize the relavent datastructures."
        super(ServiceMonitor, self).__init__(self.SENSOR_NAME,
                                                self.PRIORITY)

        self.services_to_monitor = \
            Conf.get(SSPL_CONF, f"{self.SERVICEMONITOR}>{self.MONITORED_SERVICES}", [])

        self.not_active_services = {}
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

        # Integrate into the main dbus loop to catch events
        DBusGMainLoop(set_as_default=True)
        
        # Initialize SystemBus and get Manager Interface
        self._bus = SystemBus()
        systemd = self._bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")
        self._manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')

        self.remove_disabled_services()

        return True

    def remove_disabled_services(self):
        """Remove `disabled` services from the list of services to monitor."""
        temp = self.services_to_monitor.copy()
        for service in temp:
            try:
                if 'disabled' in str(self._manager.GetUnitFileState(service)):
                    self.services_to_monitor.remove(service)
            except DBusException:
                self.services_to_monitor.remove(service)

    def run(self):
        logger.info(f"Monitoring Services : {self.services_to_monitor}")
        try:
            # Register all the services to signal of 'PropertiesChanged' and
            # raise an alert if some service is not active on initially or if
            # Unit is not found for the service
            temp_ser_to_mon = self.services_to_monitor.copy()
            for service in temp_ser_to_mon:
                err = self.connect_to_prop_changed_signal(service)
                if err:
                    self.raise_alert(service, "N/A", "N/A", "N/A", "N/A",
                        "N/A", "N/A", 0)
                    logger.error(f"{service} is not active initially. \n Error {err}")

            logger.debug(f"failed_services : {self.failed_services}")
            logger.debug(f"services_to_monitor : {self.services_to_monitor}")

            # Retrieve the main loop which will be called in the run method
            self._loop = gobject.MainLoop()

            # Initialize the gobject threads and get its context
            gobject.threads_init()
            context = self._loop.get_context()

            delay = 0
            while self.is_running():
                # At interval of 'thread_sleep' check for events occured for
                # registered services and process them(call on_pro_changed())
                context.iteration(False)
                time.sleep(self.thread_sleep)

                # At interval of 'polling_freqency' process unregistered
                # services and services with not-active state. 
                if delay == self.polling_frequency:
                    delay = 0

                    temp_ser_to_mon = self.services_to_monitor.copy()
                    for service in temp_ser_to_mon:
                        self.connect_to_prop_changed_signal(service)

                    self.check_notactive_services()

                delay+=1

            logger.debug("ServiceMonitor gracefully breaking out " +\
                                "of dbus Loop, not restarting.")
        except Exception as e:
            if self.is_running:
                logger.debug("Ungracefully breaking out of " +\
                                "dbus loop with error: %s" % e)

    def connect_to_prop_changed_signal(self, service):
        """Connect the service to the 'PropertiesChanged' Signal."""
        try:
            unit = self._bus.get_object('org.freedesktop.systemd1',\
                                        self._manager.LoadUnit(service))
            Iunit = Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')
            state = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'ActiveState'))
            substate = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'SubState'))
            pid = str(Iunit.Get('org.freedesktop.systemd1.Service', 'ExecMainPID'))

            self.update_status(service, state, substate, pid)

            Iunit2 = Interface(unit,
                            dbus_interface='org.freedesktop.systemd1.Manager')

            Iunit2.connect_to_signal('PropertiesChanged',
                                    lambda a, b, c, p = unit :
                                    self.on_prop_changed(a, b, c, p),
                                    dbus_interface=PROPERTIES_IFACE)

            logger.debug(f"{service}({pid}) state is {state}:{substate}")

            if state != "active":
                self.failed_services.append(service)
                self.raise_alert(service, "N/A", state, "N/A", substate,
                                    "N/A", pid, 0)
                logger.error(f"{service} is not active initially. state = {state}:{substate}")

            self.services_to_monitor.remove(service)

            return None
        except DBusException as err:
            return err

    def check_notactive_services(self):
        """Raise Alert if any of the not-active services has exceeded
            the threshould time for inactivity.
        """
        temp_not_active_ser = self.not_active_services.copy()
        for service, start_time in temp_not_active_ser.items():
            logger.debug(f"{service} : {start_time}, {int(time.time()) - start_time}, {self.max_wait_time}")
            if int(time.time()) - start_time > self.max_wait_time:
                state = self.service_status[service]["state"]
                substate = self.service_status[service]["substate"]
                pid = self.service_status[service]["pid"]
                self.not_active_services.pop(service)
                self.failed_services.append(service)
                self.raise_alert(service, state, state, substate, substate,
                                pid , pid, 2)

    def update_status(self, service, state, substate, pid):
        self.service_status[service] = {
            "state" : state,
            "substate" : substate,
            "pid" : pid
        }

    def on_prop_changed(self, interface, changed_properties,
                                invalidated_properties, unit):
        """Process the `PropertiesChanged` Signal from some service."""

        logger.debug("In on_prop_changed")
        Iunit = Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')
        service = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'Id'))
        state = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'ActiveState'))
        prev_state = self.service_status[service]["state"]

        logger.debug(f"{service} : {prev_state}:{state}")
        if prev_state == state:
            return

        substate = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'SubState'))
        pid = str(Iunit.Get('org.freedesktop.systemd1.Service', 'ExecMainPID'))

        prev_substate = self.service_status[service]["substate"]
        prev_pid = self.service_status[service]["pid"]

        logger.info(f"{service} changed state from " + \
                    f"{prev_state}:{prev_substate} to {state}:{substate}")

        self.update_status(service, state, substate, pid)

        self.action_per_transition(service, prev_state, state,
                    prev_substate, substate, prev_pid, pid)


    def action_per_transition(self, service, prev_state, state,
                        prev_substate, substate, prev_pid, pid):
        """Take action according to the state change of the service."""
        alert_index = -1

        logger.debug(f"in action_per_transition for {service} : " + \
            f"({prev_state}:{prev_substate}) -> ({state}:{substate})")

        if prev_state == "active" or prev_state == "reloading":
            if state == "reloading" or state == "active":
                pass  #do nothing (reload of config)
            elif state == "deactivating" or state == "inactive":
                self.not_active_services[service] = int(time.time())
            elif state == "failed":
                self.failed_services.append(service)
                alert_index = 1
            else:
                alert_index = 4
        elif prev_state == "deactivating":
            if state == "inactive" or state == "activating":
                if service not in self.not_active_services:
                    self.not_active_services[service] = int(time.time())
            elif state == "failed":
                self.failed_services.append(service)
                alert_index = 1
            else:
                alert_index = 4
        elif prev_state == "inactive" or prev_state == "failed":
            if state == "activating":
                if service not in self.not_active_services:
                    self.not_active_services[service] = int(time.time())
            elif state == "active":
                if service in self.failed_services:
                    self.failed_services.remove(service)
                    alert_index = 3
                elif service in self.not_active_services:
                    self.not_active_services.pop(service)
            else:
                alert_index = 4
        elif prev_state == "activating":
            if service in self.not_active_services:
                self.not_active_services.pop(service)
            if state == "inactive" or state == "deactivating":
                self.failed_services.append(service)
                alert_index = 1
            elif state == "active":
                if service in self.failed_services:
                    self.failed_services.remove(service)
                    alert_index = 3
                else :
                    # its a restart.
                    pass
            elif state == "failed":
                self.failed_services.append(service)
                alert_index = 1
            else:
                alert_index = 4

        logger.debug(f"alert_index : {alert_index}")
        if not self.not_active_services:
            logger.debug("Not_active_services is EMPTY")
        for s,t in self.not_active_services.items():
            logger.debug(f"{s} : {t}, {int(time.time())}")
        logger.debug(f"{self.failed_services}")

        if alert_index != -1:
            self.raise_alert(service, prev_state, state,
                prev_substate, substate, prev_pid, pid,
                alert_index)

    def raise_alert(self, service, prev_state, state, prev_substate,
                    substate, prev_pid, pid, alert_index):
        """ Send the alert to ServiceMsgHandler."""
        # Each alert info contains 4 fields
        # 1.Description | 2.Alert Type | 3.Impact | 4.Recommendation
        alert_info = [
            [f"{service} is not found/running initially",   #index 0
                "fault", "", ""],
            [f"{service} is in {state} state.",             #index 1
                "fault", "", ""],
            [f"{service} is in a non_active state for more than {self.max_wait_time} seconds.",
                "fault", "", ""],                           #index 2
            [f"{service} returned to running state.",
                "fault_resolved", "", ""],                  #index 3
            [f"service state transition from {prev_state} to {state} is not handled.",
                "missing", "", ""]                          #index 4
        ]

        description = alert_info[alert_index][0]
        alert_type = alert_info[alert_index][1]
        impact = alert_info[alert_index][2]
        recommendation = alert_info[alert_index][3]

        severity = SeverityReader().map_severity(alert_type)
        epoch_time = str(int(time.time()))
        alert_id = get_alert_id(epoch_time)
        host_name = socket.getfqdn()

        self._site_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{SITE_ID}",'DC01')
        self._rack_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{RACK_ID}",'RC01')
        self._node_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{NODE_ID}",'SN01')
        self._cluster_id = Conf.get(GLOBAL_CONF, f'{CLUSTER}>{CLUSTER_ID}','CC01')


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
                        "state" : state,
                        "previous_state" : prev_state,
                        "substate" : substate,
                        "previous_substate" : prev_substate,
                        "pid" : pid,
                        "previous_pid" : prev_pid,
                    }
                }
            }
        }
        self._write_internal_msgQ(ServiceMsgHandler.name(), alert_msg)

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
