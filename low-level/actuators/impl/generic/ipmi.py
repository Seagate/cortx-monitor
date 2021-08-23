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
  Description:       Handles messages for IPMI requests
 ****************************************************************************
"""
import subprocess

from zope.interface import implementer
from actuators.Iipmi import Iipmi

from framework.base.debug import Debug
from cortx.utils.log import Log as logger
from framework.utils.conf_utils import Conf, SSPL_CONF, IPMI, USER, PASSWORD

@implementer(Iipmi)
class IPMI(Debug):
    """Handles messages for IPMI requests"""

    ACTUATOR_NAME = "IPMI"

    # Section and keys in configuration file
    IPMI            = ACTUATOR_NAME.upper()
    USER            = 'user'
    PASS            = 'pass'


    @staticmethod
    def name():
        """ @return: name of the module."""
        return IPMI.ACTUATOR_NAME

    def __init__(self, conf_reader):
        super(IPMI, self).__init__()

        # Read in the configuration values
        self._conf_reader = conf_reader
        self._read_config()

    def perform_request(self, jsonMsg):
        """Performs the IPMI request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse out the login request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug(f"perform_request, node_request: {node_request}")

            # Parse out the arguments for the IPMI action
            ipmi_request = node_request[5:].strip().split(" ", 1)
            self._log_debug(f"perform_request, ipmi_request: {ipmi_request}")

            if len(ipmi_request) != 2:
                return "Error: IPMI request must consist of [IP] [Command]"

            ipmi_ip = ipmi_request[0]
            ipmi_req_command = ipmi_request[1].lower()

            if ipmi_req_command == "on":
                ipmi_command = f"ipmitool -I lanplus -H {ipmi_ip} -U {self._user} -P {self._pass} chassis power on"
            elif ipmi_req_command == "off":
                ipmi_command = f"ipmitool -I lanplus -H {ipmi_ip} -U {self._user} -P {self._pass} chassis power soft"
            elif ipmi_req_command == "cycle":
                ipmi_command = f"ipmitool -I lanplus -H {ipmi_ip} -U {self._user} -P {self._pass} chassis power cycle"
            elif ipmi_req_command == "status":
                ipmi_command = f"ipmitool -I lanplus -H {ipmi_ip} -U {self._user} -P {self._pass} chassis status"
            else:
                return "Error: IPMI [IP] [Command], command must be on/off/cycle/status"

            self._log_debug(f"perform_request, IP: {ipmi_ip} request: {ipmi_command}")

            # Run the command and get the response and error returned
            process = subprocess.Popen(ipmi_command, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            response, error = process.communicate()

            if error:
                response = f"{error}"

            self._log_debug(f"perform_request, IPMI response: {response}")

        except Exception as e:
            logger.exception(e)
            response = str(e)

        return response

    def _read_config(self):
        """Read in configuration values"""
        try:
            self._user = Conf.get(SSPL_CONF, f"{IPMI}>{USER}",'admin')
            self._pass = Conf.get(SSPL_CONF, f"{IPMI}>{PASSWORD}",'admin')
            logger.info("IPMI Config: user: %s" % self._user)
        except Exception as e:
            logger.exception(e)
