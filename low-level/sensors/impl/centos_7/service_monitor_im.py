import copy
import socket
import time
from collections import namedtuple
from enum import IntEnum

from dbus import PROPERTIES_IFACE, DBusException, Interface, SystemBus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib
from zope.interface import implementer

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread, ThreadException
from framework.utils.conf_utils import (CLUSTER, CLUSTER_ID, GLOBAL_CONF,
                                        NODE_ID, RACK_ID, SITE_ID, SRVNODE,
                                        SSPL_CONF, Conf)
from framework.utils.iem import Iem
from framework.utils.mon_utils import get_alert_id
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader

from message_handlers.service_msg_handler import ServiceMsgHandler
from sensors.ISystem_monitor import ISystemMonitor


UNIT_IFACE = "org.freedesktop.systemd1.Unit"
SERVICE_IFACE = "org.freedesktop.systemd1.Service"
MANAGER_IFACE = 'org.freedesktop.systemd1.Manager'
SYSTEMD_BUS = "org.freedesktop.systemd1"


class ServiceState(IntEnum):
    ACTIVE = 0
    RELOADING = 1
    INACTIVE = 2
    FAILED = 3
    ACTIVATING = 4
    DEACTIVATING = 5


class Service:

    def __init__(self, unit):
        self.unit = unit
        self.properties_iface = Interface(self.unit,
                                          dbus_interface=PROPERTIES_IFACE)
        self.service = str(self.properties_iface.Get(UNIT_IFACE, 'Id'))
        print(self.service)
        self.state = str(self.properties_iface.Get(UNIT_IFACE, 'ActiveState'))
        self.substate = str(self.properties_iface.Get(UNIT_IFACE, 'SubState'))
        self.pid = str(self.properties_iface.Get(SERVICE_IFACE, 'ExecMainPID'))
        self.previous_state = "N/A"
        self.previous_substate = "N/A"
        self.previous_pid = "N/A"
        self.properties_changed_subscribed = True
        self.alert_reported = False
        self.state_changed_time = time.time()
        self.inactive_threshold = int(
            Conf.get(SSPL_CONF,
                     f"{ServiceMonitor.name().upper()}>threshold_inactive_time",
                     60))

        self.RESOURCE_TYPE = "node:sw:os:service"
        Alert = namedtuple('Alert', ['description', 'alert_type',
                                     'impact', 'recommendation'])
        self.alerts = (
            Alert(f"{self.service} in {self.state} state.",
                  "fault",
                  f"{self.service} service is unavailable.",
                  "Try to restart the service"),
            Alert(f"{self.service} in a {self.state} state for"
                  f"more than {self.inactive_threshold} seconds.",
                  "fault",
                  f"{self.service} service is unavailable.",
                  "Try to restart the service"),
            Alert(f"{self.service} in {self.state} state.",
                  "fault_resolved",
                  f"{self.service} service is available now.",
                  "")
        )
        print(self.properties_iface.Get(
            UNIT_IFACE, 'UnitFileState'))

    @property
    def enabled(self):
        return 'disabled' not in self.properties_iface.Get(
            UNIT_IFACE, 'UnitFileState')

    @property
    def monitoring(self):
        return self.enabled and self.properties_changed_subscribed

    def is_inactive_for_threshold_time(self):
        if self.state in ["active", "failed"]:
            return False
        else:
            if time.time() - self.state_changed_time > self.inactive_threshold:
                return True
            else:
                return False

    def get_alert(self, alert_type):
        return {
            "sensor_request_type": {
                "service_status_alert": {
                    "host_id": socket.getfqdn(),
                    "severity": SeverityReader().map_severity(
                        self.alerts[alert_type].alert_type),
                    "alert_id": get_alert_id(str(int(time.time()))),
                    "alert_type": self.alerts[alert_type].alert_type,
                    "info": {
                        "site_id": Conf.get(GLOBAL_CONF,
                                            f"{CLUSTER}>{SRVNODE}>{SITE_ID}",
                                            'DC01'),
                        "cluster_id": Conf.get(GLOBAL_CONF,
                                               f'{CLUSTER}>{CLUSTER_ID}',
                                               'CC01'),
                        "rack_id": Conf.get(GLOBAL_CONF,
                                            f"{CLUSTER}>{SRVNODE}>{RACK_ID}",
                                            'RC01'),
                        "node_id": Conf.get(GLOBAL_CONF,
                                            f"{CLUSTER}>{SRVNODE}>{NODE_ID}",
                                            'SN01'),
                        "resource_type": self.RESOURCE_TYPE,
                        "resource_id": self.service,
                        "event_time": str(int(time.time())),
                        "description": self.alerts[alert_type].description,
                        "impact": self.alerts[alert_type].impact,
                        "recommendation": self.alerts[alert_type].recommendation,
                    },
                    "specific_info": {
                        "service_name": self.service,
                        "previous_state": self.previous_state,
                        "state": self.state,
                        "previous_substate": self.previous_substate,
                        "substate": self.substate,
                        "previous_pid": self.previous_pid,
                        "pid": self.pid,
                    }
                }
            }
        }


@implementer(ISystemMonitor)
class ServiceMonitor(SensorThread, InternalMsgQ):
    """ Sensor to monitor state change events of services. """

    newmethod135()

    # Section and keys in configuration file
    SERVICEMONITOR = SENSOR_NAME.upper()

    MONITORED_SERVICES = 'monitored_services'
    THREAD_SLEEP = 'thread_sleep'
    POLLING_FREQUENCY = 'polling_frequency'

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
            Conf.get(
                SSPL_CONF, f"{self.SERVICEMONITOR}>{self.MONITORED_SERVICES}",
                [])
        )
        self.services = []
        self.thread_sleep = \
            int(Conf.get(SSPL_CONF,
                f"{self.SERVICEMONITOR}>{self.THREAD_SLEEP}", 1))

        self.polling_frequency = \
            int(Conf.get(SSPL_CONF,
                f"{self.SERVICEMONITOR}>{self.POLLING_FREQUENCY}", 30))

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
        self.state_transition_graph = self.get_state_transition_graph()
        return True

    def get_state_transition_graph(self):
        graph = [[-1 for _ in ServiceState]
                 for _ in ServiceState]
        graph[ServiceState.RELOADING][ServiceState.ACTIVE] = 2
        graph[ServiceState.RELOADING][ServiceState.FAILED] = 0
        graph[ServiceState.ACTIVE][ServiceState.FAILED] = 0
        graph[ServiceState.DEACTIVATING][ServiceState.FAILED] = 0
        graph[ServiceState.DEACTIVATING][ServiceState.ACTIVE] = 2
        graph[ServiceState.INACTIVE][ServiceState.FAILED] = 0
        graph[ServiceState.INACTIVE][ServiceState.ACTIVE] = 2
        graph[ServiceState.FAILED][ServiceState.ACTIVE] = 2
        graph[ServiceState.ACTIVATING][ServiceState.INACTIVE] = 0
        graph[ServiceState.ACTIVATING][ServiceState.DEACTIVATING] = 0
        graph[ServiceState.ACTIVATING][ServiceState.ACTIVE] = 2
        graph[ServiceState.ACTIVATING][ServiceState.FAILED] = 0
        return graph

    def update_properties(self, interface, changed_properties,
                          invalidated_properties, service):

        service.previous_state = service.state
        service.previous_substate = service.substate
        service.previous_pid = service.pid

        service.state = str(service.properties_iface.Get(
            UNIT_IFACE, 'ActiveState'))
        service.substate = str(service.properties_iface.Get(
            UNIT_IFACE, 'SubState'))
        service.pid = str(service.properties_iface.Get(
            SERVICE_IFACE, 'ExecMainPID'))
        print(service.previous_state, "to", service.state)
        if service.state != service.previous_state:
            if service.state == "active":
                service.alert_reported = False
            service.state_changed_time = time.time()
            if service.monitoring:
                alert_type = self.state_transition_graph[ServiceState[service.previous_state.upper(
                )]][ServiceState[service.state.upper()]]
                if alert_type != -1:
                    alert = service.get_alert(alert_type)
                    self.raise_iem(service.service,
                                   service.alerts[alert_type].alert_type)
                    self._write_internal_msgQ(ServiceMsgHandler.name(), alert)
                    print("update_properties alert", alert)

    def run(self):
        logger.info(f"Monitoring Services : {self.services_to_monitor}")
        try:
            self.initialize_dbus()
            self.initialize_services()
            # Integrate into the main dbus loop to catch events
            logger.debug(f"services_to_monitor : {self.services_to_monitor}")

            # WHILE LOOP FUNCTION : every second we check for
            # properties change event if any generated (using context
            # iteration) and after a delay of polling frequency we
            # check for inactive processes.
            iterations = 0
            iterations_to_check_inactive_services = int(self.polling_frequency/self.thread_sleep)
            while self.is_running():
                # At interval of 'thread_sleep' check for events occured for
                # registered services and process them(call on_pro_changed())
                self.process_dbus_events()
                # At interval of 'polling_freqency' process unregistered
                # services and services with not-active (intermidiate) state.
            
                if not iterations % (iterations_to_check_inactive_services):
                    # Try to bind the enabled services on the node to the
                    # signal whose Unit was earlier not found. On successfully
                    # registering for service state change signal, remove from
                    # local list as monitoring enabled through SystemD
                    # and to avoid re-registration.
                    for service in self.services:
                        if not service.properties_changed_subscribed:
                            self.connect_to_prop_changed_signal(service)

                    # Check for services in intermidiate state(not active)
                    self.check_inactive_services()

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

    def process_dbus_events(self):
        # At interval of 'thread_sleep' check for events occured for
        # registered services and process them(call on_pro_changed())
        while self.context.pending():
            self.context.iteration(False)
        

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

        # Initialize the gobject threads and get its context
        GLib.threads_init()
        self.context = self._loop.get_context()

    def initialize_services(self):
        for service in self.services_to_monitor:
            unit = self._bus.get_object(SYSTEMD_BUS,
                                        self._manager.LoadUnit(service))
            service_obj = Service(unit)
            self.services.append(service_obj)
            self.connect_to_prop_changed_signal(service_obj)

    def connect_to_prop_changed_signal(self, service):
        """
           Bind the service to a signal('PropertiesChanged').

           Fetch the service unit from systemd and its state, substate,
           pid etc. Bind the service to the sigle which will be triggered
           whenever the service changes it's state/substate. Also raise
           an alert if service is in failed/inactive state.
        """
        try:
            Iunit2 = Interface(service.unit,
                               dbus_interface=MANAGER_IFACE)

            Iunit2.connect_to_signal('PropertiesChanged',
                                     lambda a, b, c, p=service:
                                     self.update_properties(a, b, c, p),
                                     dbus_interface=PROPERTIES_IFACE)

        except DBusException:
            if service.properties_changed_subscribed:
                alert = service.get_alert(0)
                self._write_internal_msgQ(ServiceMsgHandler.name(), alert)
                service.properties_changed_subscribed = False
        else:
            service.properties_changed_subscribed = True

    def check_inactive_services(self):
        """
           Monitor non-active Services.

           Raise FAULT Alert if any of the not-active services has exceeded
           the threshould time for inactivity.
        """
        for service in self.services:
            if service.monitoring and not service.alert_reported \
                    and service.is_inactive_for_threshold_time():
                alert = service.get_alert(1)
                self._write_internal_msgQ(ServiceMsgHandler.name(), alert)
                print("check_inactive_services", alert)
                service.alert_reported = True

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

def newmethod135():
    SENSOR_NAME = "ServiceMonitor"
    PRIORITY = 2
