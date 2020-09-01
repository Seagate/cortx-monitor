# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Handles messages for requests using hdparm tool
 ****************************************************************************
"""
import subprocess

from zope.interface import implementer
from actuators.Ihdparm import IHdparm

from framework.base.debug import Debug
from framework.utils.service_logging import logger

@implementer(IHdparm)
class Hdparm(Debug):
    """Handles messages for requests using hdparm tool"""

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
