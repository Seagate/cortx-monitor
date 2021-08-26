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
from collections import namedtuple
from queue import Queue

from dbus import PROPERTIES_IFACE, DBusException, Interface, SystemBus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from zope.interface import implementer

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread, ThreadException
from framework.base.sspl_constants import DATA_PATH
from framework.platforms.server.platform import Platform
from framework.utils.conf_utils import (SSPL_CONF, Conf)
from framework.utils.iem import Iem
from framework.utils.mon_utils import MonUtils
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from framework.utils.store_factory import store
from framework.utils.os_utils import OSUtils
from message_handlers.service_msg_handler import ServiceMsgHandler
from sensors.ISystem_monitor import ISystemMonitor

UNIT_IFACE = "org.freedesktop.systemd1.Unit"
SERVICE_IFACE = "org.freedesktop.systemd1.Service"
MANAGER_IFACE = 'org.freedesktop.systemd1.Manager'
SYSTEMD_BUS = "org.freedesktop.systemd1"
CACHE_PATH = f"/{DATA_PATH}/server/service_monitor/"

Alert = namedtuple('Alert', 'alert_type description impact recommendation')
FailedAlert = Alert("fault", "{} in {} state for more than {} seconds.",
                    "{} service is unavailable.",
                    "Try to restart the service")
InactiveAlert = Alert("fault", "{} in {} state for more than {} seconds.",
                      "{} service is unavailable.",
                      "Try to restart the service")
ResolvedAlert = Alert("fault_resolved", "{} in {} state from last {} seconds.",
                      "{} service is available now.",
                      "No action required")


class ActiveState:
    """
    State class representing monitoring state Active and actions needed to do
    when service becomes active.
    """

    @staticmethod
    def enter(service):
        for set_type in [
            service.non_active,
                service.failed_waiting_services,
                service.active_waiting_services]:
            set_type.discard(service.name)


class FailedState:
    """
    State class representing monitoring state Failed and actions needed to do
    when service raises alert(nonactive for threshold time or failed directly).
    """

    @staticmethod
    def enter(service):
        for set_type in [
            service.non_active,
                service.failed_waiting_services,
                service.active_waiting_services]:
            set_type.discard(service.name)


class InactiveState:
    """
    State class representing monitoring state Inactive and actions needed to do
    when service change state other than active or failed.
    """

    @staticmethod
    def enter(service):
        service.nonactive_enter_timestamp = time.time()
        Service.non_active.add(service.name)
        for set_type in [
                service.failed_waiting_services,
                service.active_waiting_services]:
            set_type.discard(service.name)


class DisabledState:
    """
    State class representing monitoring state Disabled and actions needed to do
    when service is disabled.
    When service enters into Disabled state, it removes signal. So, monitoring
    for particular service will be stopped.
    """

    @staticmethod
    def enter(service):
        logger.warning("{} service is disabled, it will not be "
                       "monitored".format(service.name))
        Service.non_active.discard(service.name)
        Service.monitoring_disabled.discard(service.name)
        if service.properties_changed_signal:
            service.properties_changed_signal.remove()


class EnabledState:
    """
    State class representing monitoring state Enabled and actions needed to do
    when service is enabled.
    When service enters into Enabled state, it registers signal which will be
    called when service change state.
    """

    @staticmethod
    def enter(service):
        try:
            ServiceMonitor.subscribe_properties_changed_signal(service)
            Service.monitoring_disabled.discard(service.name)
            # Call properties_changed_handler to move service into correct state
            # on start up or if service is enabled after start up
            service.properties_changed_handler("", "", "")
        except DBusException:
            service.new_unit_state(MonitoringDisabled)


class MonitoringDisabled:
    """
    State class representing monitoring state MonitoringDisabled and actions needed
    to do when signal registration for any service failed.
    """

    @staticmethod
    def enter(service):
        if service.name not in Service.monitoring_disabled:
            Service.alerts.put(ServiceMonitor.get_alert(service, FailedAlert))
        Service.monitoring_disabled.add(service.name)


class Service:
    """
    The Service class representing systemd service.
    This class use various internals states for managing service state effectively.
    """

    alerts = Queue()
    non_active = set()
    # once fault resolved detected for service, add service name
    # into the active_waiting_services list.
    active_waiting_services = set()
    # if service state changed to Failed state add service name
    # in failed_service list.
    failed_waiting_services = set()
    monitoring_disabled = set()

    def __init__(self, unit):
        """
        Initialize Service.
        """
        self.unit = unit
        self.properties_iface = Interface(self.unit,
                                          dbus_interface=PROPERTIES_IFACE)
        self.name = str(self.properties_iface.Get(UNIT_IFACE, 'Id'))
        self.state = "N/A"
        self.substate = "N/A"
        self.pid = "N/A"
        self.previous_state = "N/A"
        self.previous_substate = "N/A"
        self.previous_pid = "N/A"
        self.nonactive_enter_timestamp = time.time()
        self.waiting_timestamp = time.time()
        self.nonactive_threshold = int(
            Conf.get(SSPL_CONF,
                     f"{ServiceMonitor.name().upper()}>threshold_inactive_time",
                     '60'))
        self.threshold_waiting_time = int(Conf.get(SSPL_CONF,
                     f"{ServiceMonitor.name().upper()}>threshold_waiting_time",
                     '30'))
        self.properties_changed_signal = None
        self._service_state = ActiveState
        self._unit_state = None

    @property
    def is_enabled(self):
        if self.properties_iface.Get(UNIT_IFACE, 'UnitFileState'):
            return 'disabled' not in self.properties_iface.Get(
                UNIT_IFACE, 'UnitFileState')
        return False

    def is_nonactive_for_threshold_time(self):
        return time.time() - self.nonactive_enter_timestamp > self.nonactive_threshold

    def in_same_state_for_threshold_time(self):
        return time.time() - self.waiting_timestamp > self.threshold_waiting_time

    def new_service_state(self, new_state):
        if self._service_state != new_state:
            self._service_state = new_state
            new_state.enter(self)

    def new_unit_state(self, new_state):
        if new_state != self._unit_state:
            self._unit_state = new_state
            new_state.enter(self)

    def properties_changed_handler(self, interface, changed_properties,
                                   invalidated_properties):

        state = str(self.properties_iface.Get(
            UNIT_IFACE, 'ActiveState'))
        substate = str(self.properties_iface.Get(
            UNIT_IFACE, 'SubState'))
        pid = str(self.properties_iface.Get(
            SERVICE_IFACE, 'ExecMainPID'))
        if state != self.state:
            self.previous_state = self.state
            self.state = state
        if substate != self.substate:
            self.previous_substate = self.substate
            self.substate = substate
        if pid != self.pid:
            self.previous_pid = self.pid
            self.pid = pid

        if self.state != self.previous_state:
            if self.state == "active":
                if self._service_state is FailedState:
                    self.waiting_timestamp = time.time()
                    Service.active_waiting_services.add(self.name)
                elif self._service_state is InactiveState:
                    self.new_service_state(ActiveState)
                # TODO: Handle discarding service from state list
                # in new_service_state function.
                Service.failed_waiting_services.discard(self.name)
            elif self.state == "failed":
                if self._service_state is not FailedState:
                    self.waiting_timestamp = time.time()
                    Service.failed_waiting_services.add(self.name)
                Service.active_waiting_services.discard(self.name)
            else:
                # Avoid raising duplicate alerts
                if self._service_state != FailedState:
                    self.new_service_state(InactiveState)
                Service.active_waiting_services.discard(self.name)
                Service.failed_waiting_services.discard(self.name)
                self.dump_to_cache()

    def handle_unit_state_change(self):
        # TODO: Check if alert needs to be generated for UnitFileState change
        if self.is_enabled:
            self.new_unit_state(EnabledState)
        else:
            self.new_unit_state(DisabledState)

    @classmethod
    def from_cache(cls, service_name, unit):
        """
        Initialize service from cache
        """
        data = store.get(f"{CACHE_PATH}/{service_name}")
        service = cls(unit)
        service.new_service_state(data["service_monitor_state"])
        service.state = data["service_state"]
        service.nonactive_enter_timestamp = data["nonactive_enter_timestamp"]
        service.waiting_timestamp = data["waiting_timestamp"]
        return service

    def dump_to_cache(self):
        """
        Write service status to cache
        """
        data = {
            "service_state": self.state,
            "service_monitor_state": self._service_state,
            "nonactive_enter_timestamp": self.nonactive_enter_timestamp,
            "waiting_timestamp": self.waiting_timestamp
        }
        store.put(data, f"{CACHE_PATH}/{self.name}")

    @staticmethod
    def cache_exists(service_name):
        exists, _ = store.exists(f"{CACHE_PATH}/{service_name}")
        return exists


@implementer(ISystemMonitor)
class ServiceMonitor(SensorThread, InternalMsgQ):
    """ Sensor to monitor state change events of services. """

    SENSOR_NAME = "ServiceMonitor"
    PRIORITY = 2

    # Section and keys in configuration file
    SERVICEMONITOR = SENSOR_NAME.upper()

    THREAD_SLEEP = 'thread_sleep'
    POLLING_FREQUENCY = 'polling_frequency'

    # Dependency list
    DEPENDENCIES = {"plugins": ["SeviceMsgHandler"]}

    RESOURCE_TYPE = "node:sw:os:service"

    @staticmethod
    def name():
        """@return: name of the module."""
        return ServiceMonitor.SENSOR_NAME

    def __init__(self):
        """Initialize the relevant datastructures."""
        super(ServiceMonitor, self).__init__(self.SENSOR_NAME,
                                             self.PRIORITY)

        self.services_to_monitor = set(Platform.get_effective_monitored_services())

        self.services = {}

        self.thread_sleep = int(Conf.get(SSPL_CONF,
                                         f"{self.SERVICEMONITOR}>{self.THREAD_SLEEP}",
                                         "1"))

        self.polling_frequency = int(Conf.get(SSPL_CONF,
                                              f"{self.SERVICEMONITOR}>{self.POLLING_FREQUENCY}",
                                              "30"))

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
        self.iem.check_existing_fault_iems()
        self.KAFKA = self.iem.EVENT_CODE["KAFKA_ACTIVE"][1]

        self.initialize_dbus()
        for service in self.services_to_monitor:
            self.initialize_service(service)
        self.subscribe_unit_file_changed_signal()

        return True

    def run(self):

        try:
            logger.info(f"Monitoring Services : {self.services.keys()}")
            if not self.services_to_monitor:
                logger.info(
                    "No service to monitor, shutting down {}".format(
                        self.name()))
                self.shutdown()
            # WHILE LOOP FUNCTION : every second we check for
            # properties change event if any generated (using context
            # iteration) and after a delay of polling frequency we
            # check for non_active processes.
            iterations = 0
            non_active_check = int(
                self.polling_frequency / self.thread_sleep) or 1
            while self.is_running():
                # At interval of 'thread_sleep' check for events occurred for
                # services and process them
                self.process_events()
                self.process_alerts()
                if not iterations % non_active_check:
                    # Initialize errored service again
                    for service in self.services_to_monitor - set(
                            self.services.keys()):
                        self.initialize_service(service)
                    for service in Service.monitoring_disabled.copy():
                        self.services[service].new_unit_state(EnabledState)
                    # Check services in same state for threshold time
                    self.check_service_threshold_time()
                time.sleep(self.thread_sleep)
                iterations += 1
            logger.info("ServiceMonitor gracefully breaking out " +
                        "of dbus Loop, not restarting.")
        except GLib.Error as err:
            raise ThreadException(self.SENSOR_NAME,
                                  "Ungrecefully breaking out of"
                                  "GLib.MainLoop() with error: %s"
                                  % err)
        except DBusException as err:
            raise ThreadException(self.SENSOR_NAME,
                                  "Ungracefully breaking out of dbus loop"
                                  "with error: %s" % err)
        except Exception as err:
            raise ThreadException(self.SENSOR_NAME,
                                  "Ungracefully breaking out of"
                                  "ServiceMonitor:run() with error: %s" % err)

    def initialize_service(self, service_name):
        try:
            unit = self._bus.get_object(SYSTEMD_BUS,
                                        self._manager.LoadUnit(service_name))
            if Service.cache_exists(service_name):
                service = Service.from_cache(service_name, unit)
            else:
                service = Service(unit)
            service.handle_unit_state_change()
            self.services[service_name] = service
        except DBusException:
            logger.error("Error: {} Failed to initialize service {},"
                         "initialization will be retried in"
                         "{} seconds".format(DBusException, service_name,
                                             self.polling_frequency))

    def subscribe_unit_file_changed_signal(self):
        self._manager.connect_to_signal('UnitFilesChanged',
                                        self.unit_file_state_change_handler,
                                        dbus_interface=MANAGER_IFACE)

    @staticmethod
    def subscribe_properties_changed_signal(service):
        service.properties_changed_signal = Interface(
            object=service.unit,
            dbus_interface=MANAGER_IFACE).connect_to_signal(
            'PropertiesChanged', service.properties_changed_handler,
            PROPERTIES_IFACE)

    def unit_file_state_change_handler(self):
        for service in self.services.values():
            service.handle_unit_state_change()

    def process_events(self):
        while self.context.pending():
            self.context.iteration(False)

    def process_alerts(self):
        while not Service.alerts.empty():
            message = Service.alerts.get()
            self.raise_alert(message)

    def initialize_dbus(self):
        DBusGMainLoop(set_as_default=True)

        # Initialize SystemBus and get Manager Interface
        self._bus = SystemBus()
        systemd = self._bus.get_object(SYSTEMD_BUS,
                                       "/org/freedesktop/systemd1")
        self._manager = Interface(systemd,
                                  dbus_interface=MANAGER_IFACE)
        # Retrieve the main loop which will be called in the run method
        self._loop = GLib.MainLoop()
        self.context = self._loop.get_context()

    def check_service_threshold_time(self):
        """
            Monitor active, non-active(intermediate state) and failed services.

            Raise alert for services
            if service stays in same state for threshhold time.
        """
        for service in Service.active_waiting_services.copy():
            if self.services[service].in_same_state_for_threshold_time():
                self.services[service].new_service_state(ActiveState)
                self.raise_alert(
                    self.get_alert(self.services[service], ResolvedAlert))

        for service in Service.failed_waiting_services.copy():
            if self.services[service].in_same_state_for_threshold_time():
                self.services[service].new_service_state(FailedState)
                self.raise_alert(
                    self.get_alert(self.services[service], FailedAlert))

        for service in Service.non_active.copy():
            if self.services[service].is_nonactive_for_threshold_time():
                self.services[service].new_service_state(FailedState)
                self.raise_alert(self.get_alert(self.services[service],
                                                InactiveAlert))

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

    @classmethod
    def get_alert(cls, service, alert):
        if service.state in ["active", "failed"]:
            description = alert.description.format(
                service.name, service.state, service.threshold_waiting_time)
        else:
            description = alert.description.format(
                service.name, service.state, service.nonactive_threshold)
        return {
            "sensor_request_type": {
                "service_status_alert": {
                    "host_id": OSUtils.get_fqdn(),
                    "severity": SeverityReader().map_severity(
                        alert.alert_type),
                    "alert_id": MonUtils.get_alert_id(str(int(time.time()))),
                    "alert_type": alert.alert_type,
                    "info": {
                        "resource_type": cls.RESOURCE_TYPE,
                        "resource_id": service.name,
                        "event_time": str(int(time.time())),
                        "description": description,
                        "impact": alert.impact.format(service.name),
                        "recommendation": alert.recommendation,
                    },
                    "specific_info": {
                        "service_name": service.name,
                        "previous_state": service.previous_state,
                        "state": service.state,
                        "previous_substate": service.previous_substate,
                        "substate": service.substate,
                        "previous_pid": service.previous_pid,
                        "pid": service.pid,
                    }
                }
            }
        }

    def raise_alert(self, message):
        service = message["sensor_request_type"]["service_status_alert"][
            "info"]["resource_id"]
        alert_type = message["sensor_request_type"]["service_status_alert"][
            "alert_type"]
        self.raise_iem(service, alert_type)
        self._write_internal_msgQ(ServiceMsgHandler.name(), message)
        self.services[service].dump_to_cache()

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
