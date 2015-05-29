"""
 ****************************************************************************
 Filename:          systemd_login.py
 Description:       Handles service request messages to systemd and write
                    requests to journald
 Creation Date:     05/13/2015
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
from actuators.ILogin import ILogin

from framework.base.debug import Debug
from framework.utils.service_logging import logger

from dbus import SystemBus, Interface, exceptions as debus_exceptions
from systemd import login


class SystemdLogin(Debug):
    """Handles login request messages of systemd"""

    implements(ILogin)

    ACTUATOR_NAME = "SystemdLogin"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return SystemdLogin.ACTUATOR_NAME

    def __init__(self):
        super(SystemdLogin, self).__init__()

        # Use d-bus to communicate with systemd
        #  Described at: http://www.freedesktop.org/wiki/Software/systemd/logind/

        # Obtain an instance of d-bus to communicate with systemd
        self._bus = SystemBus()

        # Obtain a manager interface to d-bus for communications with login1
        logind = self._bus.get_object('org.freedesktop.login1',
                                       '/org/freedesktop/login1')
        self._manager = Interface(logind, dbus_interface='org.freedesktop.login1.Manager')

    def perform_request(self, jsonMsg):
        """Performs the login request"""
        self._check_debug(jsonMsg)

        # Parse out the login request to perform
        self._login_request = jsonMsg.get("actuator_request_type").get("login_controller").get("login_request")
        self._log_debug("perform_request, _login_request: %s" % self._login_request)

        result = "N/A"

        try:
            users = self._manager.ListSessions()
            for user in users:
                self._log_debug("perform_request, user: %s %s %s %s %s" % (user))

        except debus_exceptions.DBusException, error:
            logger.exception(error)

        return str(result)

    def _get_status(self):
        """"Returns the active state of the unit"""
        return self._proxy.Get('org.freedesktop.login1', 
                                'Name',
                                dbus_interface='org.freedesktop.DBus.Properties')
    