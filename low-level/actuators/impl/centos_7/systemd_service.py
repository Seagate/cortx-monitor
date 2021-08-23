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
import re

from zope.interface import implementer
from actuators.IService import IService

from framework.base.debug import Debug
from cortx.utils.log import Log as logger
from cortx.utils.service import DbusServiceHandler
from cortx.utils.process import SimpleProcess
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
        systemd = self._bus.get_object('org.freedesktop.systemd1',
                                                '/org/freedesktop/systemd1')
        self._manager = Interface(systemd,
                            dbus_interface='org.freedesktop.systemd1.Manager')

        # Subscribe to signal changes
        self._manager.Subscribe()

        # create service cls obj.
        self._service = DbusServiceHandler()

    def perform_request(self, jsonMsg):
        """Performs the service request"""
        self._check_debug(jsonMsg)

        # Parse out the service name and request to perform on it
        if jsonMsg.get("actuator_request_type").get("service_controller") \
                                                                is not None:
            self._service_name = jsonMsg.get("actuator_request_type").\
                                get("service_controller").get("service_name")
            self._service_request = jsonMsg.get("actuator_request_type").\
                        get("service_controller").get("service_request")
        else:
            self._service_name = jsonMsg.get("actuator_request_type").\
                        get("service_watchdog_controller").get("service_name")
            self._service_request = jsonMsg.get("actuator_request_type").\
                        get("service_watchdog_controller").get("service_request")

        logger.debug("perform_request, service_name: %s, service_request: %s" % \
                        (self._service_name, self._service_request))

        try:
            # Load the systemd unit for the service
            systemd_unit = self._manager.LoadUnit(self._service_name)

            # Get a proxy to systemd for accessing properties of units
            self._proxy = self._bus.get_object("org.freedesktop.systemd1", \
                                                            str(systemd_unit))

            # The returned result of the desired action
            result = {}
            is_err_response = False
            if self._service_request in ['restart', 'start']:
                # Before restart/start the service, check service state.
                # If it is not active or activating then only process
                # restart/start request.
                service_state  = self._service.get_state(self._service_name)
                state = service_state.state
                if state not in ['active','activating']:
                    if self._service_request == "restart":
                        self._service.restart(self._service_name)
                    elif self._service_request == "start":
                        self._service.start(self._service_name)
                    # Ensure we get an "active" state and not "activating"
                    service_state  = self._service.get_state(self._service_name)
                    state = service_state.state
                    max_wait = 0
                    while state != "active":
                        logger.debug("%s status is activating, needs 'active' "
                        "state after %s request has been processed, retrying"
                        % (self._service_name, self._service_request))
                        time.sleep(1)
                        max_wait += 1
                        if max_wait > 20:
                            logger.debug("maximum wait - %s seconds, for "
                                        "service restart reached." %max_wait)
                            break
                        service_state = self._service.get_state(self._service_name)
                        state = service_state.state

                else:
                    is_err_response = True
                    err_msg = ("Can not process %s request, for %s, as service "
                    "is already in %s state." %(self._service_request,
                                                    self._service_name, state))
                    logger.error(err_msg)
                    return (self._service_name, err_msg, is_err_response)

            elif self._service_request == "stop":
                self._service.stop(self._service_name)

            elif self._service_request == "status":
                # Return the status below
                service_status = self._service.get_state(self._service_name)

            # TODO: Use cortx.utils Service class methods for
            # enable/disable services.
            elif self._service_request == "enable":
                service_list = []
                service_list.append(self._service_name)

                # EnableUnitFiles() function takes second argument as boolean.
                # 'True' will enable a service for runtime only(creates symlink
                #  in /run/.. directory) 'False' will enable a service
                #  persistently (creates symlink in /etc/.. directory)
                _, dbus_result = self._manager.EnableUnitFiles(service_list,
                                                                False, True)
                res = parse_enable_disable_dbus_result(dbus_result)
                result.update(res)
                logger.debug("perform_request, result for enable request: "
                                                    "result: %s" % (result))

            elif self._service_request == "disable":
                service_list = []
                service_list.append(self._service_name)

                # DisableUnitFiles() function takes second argument as boolean.
                # 'True' will disable a service for runtime only(removes symlink
                # from /run/.. directory) 'False' will disable a service
                # persistently(removes symlink from /etc/.. directory)
                dbus_result = self._manager.DisableUnitFiles(service_list, False)
                res = parse_enable_disable_dbus_result(dbus_result)
                result.update(res)
                logger.debug("perform_request, result for disable request: %s"
                                                                    % result)
            else:
                logger.error("perform_request, Unknown service request - %s "
                                "for service - %s" %(self._service_request,
                                self._service_name))
                is_err_response = True
                return (self._service_name, "Unknown service request",
                                                            is_err_response)

        except debus_exceptions.DBusException as error:
            is_err_response = True
            logger.exception("DBus Exception: %r" % error)
            return (self._service_name, str(error),  is_err_response)

        except Exception as ae:
            logger.exception("SystemD Exception: %r" % ae)
            is_err_response = True
            return (self._service_name, str(ae), is_err_response)

        # Give the unit some time to finish starting/stopping to get final status
        time.sleep(5)

        # Get the current status of the process and return it back:
        service_status = self._service.get_state(self._service_name)
        pid = service_status.pid
        state = service_status.state
        substate = service_status.substate
        status = self._service.is_enabled(self._service_name)
        uptime = get_service_uptime(self._service_name)
        # Parse dbus output to fetch command line path with args.
        command_line = service_status.command_line_path
        command_line_path_with_args = []
        for field in list(command_line[0][1]):
            command_line_path_with_args.append(str(field))
        result["pid"] = pid
        result["state"] = state
        result["substate"] = substate
        result["status"] = status
        result["uptime"] = uptime
        result["command_line_path"] = command_line_path_with_args

        logger.debug("perform_request, state: %s, substate: %s" %
                                (str(state), str(substate)))
        return (self._service_name, result, is_err_response)

def parse_enable_disable_dbus_result(dbus_result):
    """Parse debus output and add in dictionary."""
    # Parse dbus output.
    # dbus o/p: dbus.Array([dbus.Struct((dbus.String('symlink'),
    # dbus.String('/etc/systemd/system/multi-user.target.wants/statsd.service'),
    # dbus.String('/usr/lib/systemd/system/statsd.service')), signature=None)],
    # signature=dbus.Signature('(sss)'))
    result = {}
    key = None
    if list(dbus_result):
        dbus_result = list(dbus_result[0])
        for field in dbus_result:
            if field in ["symlink", "unlink"]:
                key = field
                result[key] = []
                continue
            elif field:
                result[key].append(str(field))
    return result

def get_service_uptime(service_name):
    """Get service uptime."""
    uptime = "NA"
    cmd = f"systemctl status {service_name} "
    output, error, returncode = SimpleProcess(cmd).run()
    if returncode != 0:
        logger.error("get_service_timestamp: CMD %s failed to get timestamp "
                                            "due to error: %s" %(cmd, error))
    else:
        output=output.decode('utf-8')
        timestamp_status = r"Active:(.*) since (.*)"
        for line in output.splitlines():
            status_line = re.search(timestamp_status, line)
            if status_line:
                uptime = status_line.group(2).strip()
    return uptime