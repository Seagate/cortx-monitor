"""
 ****************************************************************************
 Filename:          systemd_service.py
 Description:       Handles service request messages to systemd and write
                    requests to journald
 Creation Date:     03/25/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import time

from zope.interface import implements
from actuators.IService import IService

from framework.base.debug import Debug
from framework.utils.service_logging import logger

from dbus import SystemBus, Interface, exceptions as debus_exceptions


class SystemdService(Debug):
    """Handles service request messages to systemd"""

    implements(IService)

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
        self._manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')

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

            if self._service_request == "restart":
                self._manager.RestartUnit(self._service_name, 'replace')
                result = self._get_status()
                self._log_debug("perform_request restart: %s" % result)

            elif self._service_request == "start":
                self._manager.StartUnit(self._service_name, 'replace')

            elif self._service_request == "stop":
                self._manager.StopUnit(self._service_name, 'replace')

            elif self._service_request == "status":
                # Return the status below
                pass

            else:
                self._log_debug("perform_request, Unknown service request")
                return self._service_name, "Unknown service request"

        except debus_exceptions.DBusException, error:
            logger.exception(error)
            return self._service_name, str(error)

        # Give the unit some time to finish starting/stopping to get final status
        time.sleep(5)

        # Get the current status of the process and return it back
        result = self._get_status()
        self._log_debug("perform_request, status: %s" % result)

        return self._service_name, result

    def _get_status(self):
        """"Returns the active state of the unit"""
        return self._proxy.Get('org.freedesktop.systemd1.Unit', 
                                'ActiveState',
                                dbus_interface='org.freedesktop.DBus.Properties')
    
