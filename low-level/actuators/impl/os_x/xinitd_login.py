"""
 ****************************************************************************
 Filename:          xinitd_service.py
 Description:       Handles login request messages to xinitd
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


from zope.interface import implements
from actuators.ILogin import ILogin

from framework.base.debug import Debug


class XinitdLogin(Debug):
    """Handles login request messages to xinitd"""

    implements(ILogin)

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
            