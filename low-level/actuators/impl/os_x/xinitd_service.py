"""
 ****************************************************************************
 Filename:          xinitd_service.py
 Description:       Handles service request messages to xinitd
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

from zope.interface import implements
from actuators.IService import IService

from framework.base.debug import Debug
from framework.utils.service_logging import logger

from dbus import SystemBus, Interface, exceptions as debus_exceptions


class XinitdService(Debug):
    """Handles service request messages to systemd"""

    implements(IService)
    
    ACTUATOR_NAME = "XinitdService"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return XinitdService.ACTUATOR_NAME

    def __init__(self):
        super(XinitdService, self).__init__()

    def perform_request(self, jsonMsg):
        """Performs the request"""
        self._check_debug(jsonMsg)

        # Parse out the service name and request to perform on it
        self._service_name = jsonMsg.get("actuator_request_type").get("service_controller").get("service_name")
        self._service_request = jsonMsg.get("actuator_request_type").get("service_controller").get("service_request")
        self._log_debug("perform_request, service_name: %s, service_request: %s" % \
                        (self._service_name, self._service_request))

        
        # Code to handle service requests using xinitd here...
        

    