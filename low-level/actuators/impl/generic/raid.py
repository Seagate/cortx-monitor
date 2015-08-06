"""
 ****************************************************************************
 Filename:          raid.py
 Description:       Handles messages for RAID requests
 Creation Date:     07/08/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import subprocess

from zope.interface import implements
from actuators.Iraid import IRAIDactuator

from framework.base.debug import Debug
from framework.utils.service_logging import logger

class RAIDactuator(Debug):
    """Handles request messages for RAID requests"""

    implements(IRAIDactuator)

    ACTUATOR_NAME = "RAIDactuator"


    @staticmethod
    def name():
        """ @return: name of the module."""
        return RAIDactuator.ACTUATOR_NAME

    def __init__(self):
        super(RAIDactuator, self).__init__()

    def perform_request(self, jsonMsg):
        """Performs the RAID request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse out the login request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("perform_request, node_request: %s" % node_request)

            # Parse out the arguments for the RAID action
            raid_request = node_request[5:].strip()
            self._log_debug("perform_request, raid_request: %s" % raid_request)

            command = "sudo /usr/sbin/mdadm --{0}".format(raid_request)
            self._log_debug("perform_request, executing RAID command: %s" % command)

            # Run the command and get the response and error returned
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            response, error = process.communicate()

            if error:
                response = "Error: {0}".format(error)

            self._log_debug("perform_request, RAID response: %s" % response)

        except Exception as e:
            logger.exception(e)
            response = str(e)

        return response
