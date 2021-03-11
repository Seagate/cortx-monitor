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
import json

from dbus import Interface, SystemBus, DBusException, PROPERTIES_IFACE
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject as gobject

from zope.interface import implementer
from sensors.ISystem_monitor import ISystemMonitor
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from message_handlers.service_msg_handler import ServiceMsgHandler
from framework.utils.service_logging import logger

from framework.utils.conf_utils import (GLOBAL_CONF, CLUSTER, SRVNODE, SITE_ID,
                RACK_ID, NODE_ID, CLUSTER_ID, SSPL_CONF, Conf)
from framework.utils.severity_reader import SeverityReader
from framework.utils.mon_utils import get_alert_id
from cortx.utils.service import Service, ServiceError

@implementer(ISystemMonitor)
class ServiceMonitor(SensorThread, InternalMsgQ):
    """Sensor to monitor state change events of services."""

    SENSOR_NAME       = "ServiceMonitor"
    PRIORITY          = 2

    # Section and keys in configuration file
    SERVICEMONITOR     = SENSOR_NAME.upper()
    RESOURCE_TYPE      = "node:sw:os:service"
    MONITORED_SERVICES = 'monitored_services'
    MAX_WAIT_TIME      = 'threshold_inactive_time'

    # Dependency list
    DEPENDENCIES = {"plugins": ["SeviceMsgHandler"]}

    @staticmethod
    def name():
        """@return: name of the module."""
        return ServiceMonitor.SENSOR_NAME

    def __init__(self):
        super(ServiceMonitor, self).__init__(self.SENSOR_NAME,
                                                self.PRIORITY)
        logger.info("__init__ call from ServiceMonitor")
        self.services_to_monitor = \
            Conf.get(SSPL_CONF, f"{self.SERVICEMONITOR}>{self.MONITORED_SERVICES}", [])
        self.remove_disabled_services()

        logger.info("from ServiceMonitor : ", self.services_to_monitor)
        self.initial_alert_sent = False

        self.monitored_services = []
        self.not_active_services = {}
        self.failed_services = []

        self.service_status = {}

        self.max_wait_time = \
            int(Conf.get(SSPL_CONF, f"{self.SERVICEMONITOR}>{self.MAX_WAIT_TIME}", 120))

    def read_data(self):
        """Return the dict of service status'"""
        return self.service_status

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(ServiceMonitor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(ServiceMonitor, self).initialize_msgQ(msgQlist)

        # Integrate into the main dbus loop to catch events
        DBusGMainLoop(set_as_default=True)

        self._bus = SystemBus()
        systemd = self._bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")
        self._manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')

        return True


    def remove_disabled_services(self):
        temp = self.services_to_monitor
        for service in temp:
            try:
                if 'disabled' in Service('dbus').is_enabled(service):
                    self.services_to_monitor.remove(service)
            except ServiceError:
                self.services_to_monitor.remove(service)

    def run(self):
        # method will be re-executed after fixed interval (eg : 30s)
        logger.info("In run() of ServiceMonitor")
        for service in self.services_to_monitor:
            try:
                unit = self._bus.get_object('org.freedesktop.systemd1',\
                                            self._manager.LoadUnit(service))
                Iunit = Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')
                state = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'ActiveState'))
                substate = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'SubState'))
                pid = str(Iunit.Get('org.freedesktop.systemd1.Service', 'ExecMainPID'))

                if state != "active":
                    if not self.initial_alert_sent:
                        self.raise_alert(service, "N/A", state, "N/A", substate,
                                         "N/A", pid, 0)
                        logger.error(f"{service} is not active initially. state = {state}:{substate}")
                    continue

                self.update_states(service, state, substate, pid)

                Iunit2 = Interface(unit,
                                dbus_interface='org.freedesktop.systemd1.Manager')

                Iunit2.connect_to_signal('PropertiesChanged',
                                        lambda a, b, c, p = unit :
                                        self.on_prop_changed(a, b, c, p),
                                        dbus_interface=PROPERTIES_IFACE)

                logger.info(f"{service}({pid}) state is {state}:{substate}")
                if self.initial_alert_sent:
                    self.raise_alert(service, "N/A", state, "N/A", substate,
                                     "N/A", pid, 3)
                    logger.info(f"{service} has returned to {state} state")

                self.services_to_monitor.remove(service)
                self.monitored_services.append(service)
            except DBusException as err:
                self.raise_alert(service, "N/A", "N/A", "N/A", "N/A",
                    "N/A", "N/A", 0)
                logger.error(f"{service} is not active initially. \n Error {err}")

        self.initial_alert_sent = True

        for service, start_time in self.not_active_services.items():
            if int(time.time()) - start_time > self.max_wait_time:
                state = self.service_status[service]["state"]
                substate = self.service_status[service]["substate"]
                pid = self.service_status[service]["pid"]
                self.raise_alert(service, state, state, substate, substate,
                                pid , pid, 2)

        self.loop = gobject.MainLoop()
        self.loop.run()

    def update_states(self, service, state, substate, pid):
        self.service_status[service] = {
            "state" : state,
            "substate" : substate,
            "pid" : pid
        }

    def on_prop_changed(self, interface, changed_properties,
                                invalidated_properties, unit):
        Iunit = self._bus.Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')
        service = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'Id'))
        state = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'ActiveState'))
        prev_state = self.service_status[service]["state"]

        if prev_state == state:
            return

        substate = str(Iunit.Get('org.freedesktop.systemd1.Unit', 'SubState'))
        pid = str(Iunit.Get('org.freedesktop.systemd1.Service', 'ExecMainPID'))

        prev_substate = self.service_status[service]["substate"]
        prev_pid = self.service_status[service]["pid"]

        logger.info(f"{service} changed state from " + \
                    f"{prev_state}:{prev_substate} to {state}:{substate}")

        self.action_per_transition(service, prev_state, state,
                    prev_substate, substate, prev_pid, pid)

        self.update_states(service, state, substate, pid)

    def action_per_transition(self, service, prev_state, state,
                        prev_substate, substate, prev_pid, pid):

        alert_index = -1

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
        elif prev_state == "inactive":
            if state == "activating":
                if service not in self.not_active_services:
                    self.not_active_services[service] = int(time.time())
            else:
                alert_index = 4
        elif prev_state == "activating":
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

        if alert_index != -1:
            self.raise_alert(service, prev_state, state,
                prev_substate, substate, prev_pid, pid,
                alert_index)

    def raise_alert(self, service, prev_state, state, prev_substate,
                    substate, prev_pid, pid, alert_index):

        alert_info = [
            [f"{service} is not found/running initially",   #0
                "fault", "", ""],
            [f"{service} is in {state} state.",             #1
                "fault", "", ""],
            [f"{service} is in a non_active state for more than {self.MAX_WAIT_TIME} seconds.",
                "fault", "", ""],                           #2
            [f"{service} returned to running state.",
                "fault_resolved", "", ""],                  #3
            [f"service state transition from {prev_state} to {state} is not handled.",
                "missing", "", ""]                          #4
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
        """Suspend the module thread. It should be non-blocking"""
        super(ServiceMonitor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(ServiceMonitor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(ServiceMonitor, self).shutdown()
