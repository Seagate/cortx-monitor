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
  Description:       Handles service request messages to systemd and write
                    requests to journald
 ****************************************************************************
"""

from zope.interface import implementer
from actuators.ILogin import ILogin

from framework.base.debug import Debug
from framework.utils.service_logging import logger

from dbus import SystemBus, Interface, exceptions as debus_exceptions


@implementer(ILogin)
class SystemdLogin(Debug):
    """Handles login request messages of systemd"""

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
        self._login_request = jsonMsg.get("login_request")
        self._log_debug("perform_request, _login_request: %s" % self._login_request)

        user_names = []

        try:
            # Return a list of user names currently logged in
            if self._login_request == "get_all_users":
                users = self._manager.ListSessions()
                for user in users:
                    # session id, user id, user name, seat id, session object path
                    if user[2] not in user_names:
                        self._log_debug("perform_request, user name: %s" % (user[2]))
                        user_names.append(user[2])

        except debus_exceptions.DBusException as error:
            logger.exception(error)
            self._bus = None
            self._manager = None

        return user_names

    def _get_status(self):
        """"Returns the active state of the unit"""
        return self._proxy.Get('org.freedesktop.login1',
                                'Name',
                                dbus_interface='org.freedesktop.DBus.Properties')

