# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Handles service request messages to systemd
 ****************************************************************************
"""

import json
import time

from zope.interface import implementer
from actuators.IService import IService

from framework.base.debug import Debug
from framework.utils.service_logging import logger

from dbus import SystemBus, Interface, exceptions as debus_exceptions

@implementer(IService)
class SystemdService(Debug):
    """Handles service request messages to systemd"""

    ACTUATOR_NAME = "SystemdService"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return SystemdService.ACTUATOR_NAME

    def __init__(self):
        super(SystemdService, self).__init__()

        # Use d-bus to communicate with systemd
        #  Described at: http://www.freedesktop.org/wiki/Software/systemd/dbus/

        # Obtain an instance of d-bus to communicate with systemd
        self._bus = SystemBus()

        # Obtain a manager interface to d-bus for communications with systemd
        systemd = self._bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
        self._manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')

        # Subscribe to signal changes
        self._manager.Subscribe()

    def perform_request(self, jsonMsg):
        """Performs the service request"""
        self._check_debug(jsonMsg)

        # Parse out the service name and request to perform on it
        if jsonMsg.get("actuator_request_type").get("service_controller") is not None:
            self._service_name = jsonMsg.get("actuator_request_type").get("service_controller").get("service_name")
            self._service_request = jsonMsg.get("actuator_request_type").get("service_controller").get("service_request")
        else:
            self._service_name = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("service_name")
            self._service_request = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("service_request")

        self._log_debug("perform_request, service_name: %s, service_request: %s" % \
                        (self._service_name, self._service_request))

        try:
            # Load the systemd unit for the service
            systemd_unit = self._manager.LoadUnit(self._service_name)

            # Get a proxy to systemd for accessing properties of units
            self._proxy = self._bus.get_object("org.freedesktop.systemd1", str(systemd_unit))

            # The returned result of the desired action
            result = None

            if self._service_request == "restart":
                self._manager.RestartUnit(self._service_name, 'replace')

                # Ensure we get an "active" status and not "activating"
                max_wait = 0
                while self._get_activestate() != "active":
                    self._log_debug("status is still activating, pausing")
                    time.sleep(1)
                    max_wait += 1
                    if max_wait > 20:
                        self._log_debug("maximum wait for service restart reached")
                        break

            elif self._service_request == "start":
                self._manager.StartUnit(self._service_name, 'replace')

            elif self._service_request == "stop":
                self._manager.StopUnit(self._service_name, 'replace')

            elif self._service_request == "status":
                # Return the status below
                state = self._get_activestate()
                substate = self._get_active_substate()
                self._log_debug("perform_request, state: %s, substate: %s" %
                                (str(state), str(substate)))
                return (self._service_name, state, substate, False)

            elif self._service_request == "enable":
                service_list = []
                service_list.append(self._service_name)

                """EnableUnitFiles() function takes second argument as boolean.
                   True will enable a service for runtime only(creates symlink in /run/.. directory)
                   False will enable a service persistently(creates symlink in /etc/.. directory)"""
                bool_res, dbus_result = self._manager.EnableUnitFiles(service_list, False, True)
                # Parse dbus output.
                if list(dbus_result):
                    result = []
                    for field in list(dbus_result)[0]:
                        result.append(field)
                self._log_debug("perform_request, bool: %s, result: %s" % (bool_res, result))

            elif self._service_request == "disable":
                service_list = []
                service_list.append(self._service_name)

                """DisableUnitFiles() function takes second argument as boolean.
                   True will disable a service for runtime only(removes symlink from /run/.. directory)
                   False will disable a service persistently(removes symlink from /etc/.. directory)"""
                dbus_result = self._manager.DisableUnitFiles(service_list, False)
                # Parse dbus output.
                if list(dbus_result):
                    result = []
                    for field in list(dbus_result)[0]:
                        if field:
                            result.append(str(field))

                self._log_debug("perform_request, result: %s" % result)

            else:
                self._log_debug("perform_request, Unknown service request")
                return (self._service_name, "Unknown service request", None, True)

        except debus_exceptions.DBusException as error:
            logger.exception("DBus Exception: %r" % error)
            return (self._service_name, str(error), None, True)

        except Exception as ae:
            logger.exception("Exception: %r" % ae)
            return (self._service_name, str(ae), None, True)

        # Give the unit some time to finish starting/stopping to get final status
        time.sleep(5)

        # Get the current status of the process and return it back if no result
        if result is None:
            state = self._get_activestate()
            substate = self._get_active_substate()
            self._log_debug("perform_request, state: %s, substate: %s" %
                                (str(state), str(substate)))
            return (self._service_name, state, substate, False)

        if not isinstance(result, list):
            result = str(result)
        return (self._service_name, result, None, False)

    def _get_activestate(self):
        """"Returns the active state of the unit"""
        return self._proxy.Get('org.freedesktop.systemd1.Unit',
                                'ActiveState',
                                dbus_interface='org.freedesktop.DBus.Properties')

    def _get_active_substate(self):
        """"Returns the active state of the unit"""
        return self._proxy.Get('org.freedesktop.systemd1.Unit',
                                'SubState',
                                dbus_interface='org.freedesktop.DBus.Properties')

    def is_service_enabled(self, service_name):
        """Check service status : disabled/enabled"""
        state = str(self._manager.GetUnitFileState(service_name))
        if state == 'enabled':
            return True, state
        else:
            return False, state

    def get_service_info(self, service_name):
        """Fetch service_pid and other informatrion."""
        unit = self._bus.get_object('org.freedesktop.systemd1',self._manager.GetUnit(service_name))
        Iunit = Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')
        curr_pid = str(Iunit.Get('org.freedesktop.systemd1.Service', 'ExecMainPID'))
        command_line =  list(Iunit.Get('org.freedesktop.systemd1.Service', 'ExecStart'))
        command_line = str(command_line[0][0])
        _, service_substate = self.is_service_enabled(service_name)
        return curr_pid, command_line, service_substate
