"""
 ****************************************************************************
 Filename:          hdparm.py
 Description:       Handles messages for requests using hdparm tool
 Creation Date:     11/10/2015
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
from actuators.Ihdparm import IHdparm

from framework.base.debug import Debug
from framework.utils.service_logging import logger

class Hdparm(Debug):
    """Handles messages for requests using hdparm tool"""

    implements(IHdparm)

    ACTUATOR_NAME = "Hdparm"


    @staticmethod
    def name():
        """ @return: name of the module."""
        return Hdparm.ACTUATOR_NAME

    def __init__(self):
        super(Hdparm, self).__init__()

    def perform_request(self, jsonMsg):
        """Performs the Hdparm request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse out the node request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("perform_request, node_request: %s" % node_request)

            # Parse out the drive to power cycle on
            hdparm_request = node_request[8:].strip()
            self._log_debug("perform_request, hdparm request: %s" % hdparm_request)

            # Build the desired command using hdparm tool
            command = "sudo /usr/sbin/hdparm {0}".format(hdparm_request)
            self._log_debug("perform_request, executing command: %s" % command)

            # Run the command and get the response and error returned
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            response, error = process.communicate()
            # If an error exists stop here and return the response
            if error:
                response = "Error: {0}".format(error)
                return response

        except Exception as e:
            logger.exception(e)
            response = str(e)

        return response