"""
 ****************************************************************************
 Filename:          systemd_watchdog.py
 Description:       Monitors Centos 7 systemd for service events and notifies
                    the ServiceMsgHandler
 Creation Date:     04/27/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os
import json
import shutil
import Queue
import pyinotify
import time

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from message_handlers.service_msg_handler import ServiceMsgHandler

from zope.interface import implements
from sensors.IService_watchdog import IServiceWatchdog

import dbus
from dbus import SystemBus, Interface
import gobject
from dbus.mainloop.glib import DBusGMainLoop
from systemd import journal


class SystemdWatchdog(ScheduledModuleThread, InternalMsgQ):

    implements(IServiceWatchdog)

    SENSOR_NAME       = "SystemdWatchdog"
    PRIORITY          = 2

    # Section and keys in configuration file
    SYSTEMDWATCHDOG    = SENSOR_NAME.upper()
    MONITORED_SERVICES = 'monitored_services'


    @staticmethod
    def name():
        """@return: name of the module."""
        return SystemdWatchdog.SENSOR_NAME

    def __init__(self):
        super(SystemdWatchdog, self).__init__(self.SENSOR_NAME,
                                                  self.PRIORITY)
        # Mapping of services and their status'
        self._service_status = {}
        self._inactive_services = []

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(SystemdWatchdog, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(SystemdWatchdog, self).initialize_msgQ(msgQlist)

    def read_data(self):
        """Return the dict of service status'"""
        return self._service_status

    def run(self):
        """Run the monitoring periodically on its own thread."""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        self._log_debug("Start accepting requests")

        try:
            # Integrate into the main dbus loop to catch events
            DBusGMainLoop(set_as_default=True)

            # Connect to dbus system wide
            self._bus = SystemBus()

            # Get an instance of systemd1
            systemd = self._bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")

            # Use the systemd object to get an interface to the Manager
            self._manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')

            # Read in the list of services to monitor
            monitored_services = self._get_monitored_services()

            # Retrieve a list of all the service units
            units = self._manager.ListUnits()

            #  Start out assuming their all inactive
            self._inactive_services = list(monitored_services)

            logger.info("SystemdWatchdog, Monitored services listed in conf file: %s" % monitored_services)
            logger.info("SystemdWatchdog, Monitoring the following Services:")

            total = 0
            for unit in units:

                if ".service" in unit[0]:
                    unit_name = unit[0]

                    # Apply the filter from config file if present
                    if monitored_services:
                        if unit_name not in monitored_services:
                            continue
                    logger.info("    " + unit_name)

                    # Remove it from our inactive list; it's alive and well
                    self._inactive_services.remove(unit_name)
                    total += 1

                    # Retrieve an object representation of the systemd unit
                    unit = self._bus.get_object('org.freedesktop.systemd1',
                                                self._manager.GetUnit(unit_name))

                    # Use the systemd unit to get an Interface to call methods
                    Iunit = Interface(unit,
                                      dbus_interface='org.freedesktop.systemd1.Manager')

                    # Connect the PropertiesChanged signal to the unit and assign a callback
                    Iunit.connect_to_signal('PropertiesChanged',
                                            lambda a, b, c, p = unit :
                                            self._on_prop_changed(a, b, c, p),
                                            dbus_interface=dbus.PROPERTIES_IFACE)
                    self._service_status[str(unit)] = "active"

            logger.info("SystemdWatchdog, Total services monitored: %d" % total)

            # Retrieve the main loop which will be called in the run method
            self._loop = gobject.MainLoop()

            # Initialize the gobject threads and get its context
            gobject.threads_init()
            context = self._loop.get_context()

            # Send out the current status of each monitored service
            for service in monitored_services:
                try:
                    msgString = json.dumps({"actuator_request_type": {
                                    "service_watchdog_controller": {
                                        "service_name" : service,
                                        "service_request" : "status",
                                        "previous_state" : "N/A"
                                        }
                                    }
                                 })
                    self._write_internal_msgQ(ServiceMsgHandler.name(), msgString)

                except Exception:
                    logger.exception()

            logger.info("SystemdWatchdog initialization completed")

            # Leave enabled for now, it's not too verbose and handy in logs when status' change
            self._set_debug(True)
            self._set_debug_persist(True)

            # Loop forever iterating over the context
            while self._running == True:
                context.iteration(True)
                time.sleep(2)

                if len(self._inactive_services) > 0:
                    self._examine_inactive_services()

            self._log_debug("SystemdWatchdog gracefully breaking out " \
                                "of dbus Loop, not restarting.")

        except Exception as ae:
            # Check for debug mode being activated when it breaks out of blocking loop
            self._read_my_msgQ_noWait()
            if self.is_running() == True:
                self._log_debug("Ungracefully breaking " \
                                "out of dbus loop with error: %r" % ae)
                # Let the top level sspl_ll_d know that we have a fatal error
                #  and shutdown so that systemd can restart it
                raise Exception(ae)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        self._log_debug("Finished processing successfully")

    def _examine_inactive_services(self):
        """See if an inactive service has been successfully started
            and if so attach a callback method to its properties
            to detect changes
        """
        for disabled_service in self._inactive_services:
            # Retrieve an object representation of the systemd unit
            unit = self._bus.get_object('org.freedesktop.systemd1',
                                        self._manager.LoadUnit(disabled_service))

            state = unit.Get('org.freedesktop.systemd1.Unit', 'ActiveState',
                             dbus_interface='org.freedesktop.DBus.Properties')

            substate = unit.Get('org.freedesktop.systemd1.Unit', 'SubState',
                             dbus_interface='org.freedesktop.DBus.Properties')

            if state == "active":
                self._log_debug("Service: %s is now active and being monitored!" %
                                disabled_service)
                self._service_status[str(disabled_service)] = str(state) + ":" + str(substate)

                # Use the systemd unit to get an Interface to call methods
                Iunit = Interface(unit,
                                  dbus_interface='org.freedesktop.systemd1.Manager')

                # Connect the PropertiesChanged signal to the unit and assign a callback
                Iunit.connect_to_signal('PropertiesChanged',
                                         lambda a, b, c, p = unit :
                                         self._on_prop_changed(a, b, c, p),
                                         dbus_interface=dbus.PROPERTIES_IFACE)

                self._inactive_services.remove(disabled_service)

                # Send out notification of the state change
                msgString = json.dumps({"actuator_request_type": {
                                    "service_watchdog_controller": {
                                        "service_name" : disabled_service,
                                        "service_request": "status",
                                        "previous_state" : "inactive"
                                        }
                                    }
                                 })
                self._write_internal_msgQ(ServiceMsgHandler.name(), msgString)

        if len(self._inactive_services) == 0:
            self._log_debug("Successfully monitoring all services now!")

    def _get_prop_changed(self, unit, interface, prop_name, changed_properties, invalidated_properties):
        """Retrieves the property that changed"""
        if prop_name in invalidated_properties:
            return unit.Get(interface, prop_name, dbus_interface=dbus.PROPERTIES_IFACE)
        elif prop_name in changed_properties:
            return changed_properties[prop_name]
        else:
            return None

    def _on_prop_changed(self, interface, changed_properties, invalidated_properties, unit):
        """Callback to handle state changes in services"""
        # We're dealing with systemd units so we only care about that interface
        #self._log_debug("_on_prop_changed, interface: %s" % interface)
        if interface != 'org.freedesktop.systemd1.Unit':
            return

        # Get the interface for the unit
        Iunit = Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')

        # Always call methods on the interface not the actual object
        unit_name = Iunit.Get(interface, "Id")
        self._log_debug("_on_prop_changed, unit_name: %s" % unit_name)
        # self._log_debug("_on_prop_changed, changed_properties: %s" % changed_properties)
        # self._log_debug("_on_prop_changed, invalids: %s" % invalidated_properties)

        state = self._get_prop_changed(unit, interface, "ActiveState",
                                       changed_properties, invalidated_properties)

        substate = self._get_prop_changed(unit, interface, "SubState",
                                          changed_properties, invalidated_properties)

        # The state can change from an incoming json msg to the service msg handler
        #  This provides a catch to make sure that we don't send redundant msgs
        if self._service_status.get(str(unit_name), "") == str(state) + ":" + str(substate):
            self._log_debug("_on_prop_changed, no service state change detected, ignoring.")
            return
        else:
            # Update the state in the global dict for later use
            self._log_debug("_on_prop_changed, service state change detected notifying ServiceMsgHandler.")
            previous_service_status = self._service_status.get(str(unit_name), "").split(":")[0]
            if not previous_service_status:
                previous_service_status = "inactive"
            self._service_status[str(unit_name)] = str(state) + ":" + str(substate)

        # Only send out a json msg if there was a state or substate change for the service
        if state or substate:
            self._log_debug("_on_prop_changed, State: %s, Substate: %s" % (state, substate))

            # Notify the service message handler to transmit the status of the service
            if unit_name is not None:
                msgString = json.dumps({"actuator_request_type": {
                                "service_watchdog_controller": {
                                    "service_name" : unit_name,
                                    "service_request": "status",
                                    "previous_state" : previous_service_status
                                    }
                                }
                             })
                self._write_internal_msgQ(ServiceMsgHandler.name(), msgString)

                if state == "inactive":
                    self._inactive_services.append(unit_name)

    def _get_monitored_services(self):
        """Retrieves the list of services to be monitored"""
        return self._conf_reader._get_value_list(self.SYSTEMDWATCHDOG,
                                                 self.MONITORED_SERVICES)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(SystemdWatchdog, self).shutdown()