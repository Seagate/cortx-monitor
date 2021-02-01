# Copyright (c) 2001-2015 Seagate Technology LLC and/or its Affiliates
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
  Description:       Handles login request messages to xinitd
 ****************************************************************************
"""


from zope.interface import implementer
from cortx.sspl.actuators.ILogin import ILogin
from cortx.sspl.framework.base.debug import Debug

@implementer(ILogin)
class XinitdLogin(Debug):
    """Handles login request messages to xinitd"""

    ACTUATOR_NAME = "XinitdLogin"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return XinitdLogin.ACTUATOR_NAME

    def __init__(self):
        super(XinitdLogin, self).__init__()

    def perform_request(self, jsonMsg):
        """Performs the login request"""
        self._check_debug(jsonMsg)

        # Parse out the login request to perform
        self._login_request = jsonMsg.get("login_request")
        self._log_debug("perform_request, _login_request: %s" % self._login_request)

        # Code to handle login requests using xinitd here...

        test_names=["jake", "joe", "root"]
        return test_names
