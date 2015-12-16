"""
 ****************************************************************************
 Filename:          ipmi.py
 Description:       Handles messages for IPMI requests
 Creation Date:     08/05/2015
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
from actuators.Iipmi import Iipmi

from framework.base.debug import Debug
from framework.utils.service_logging import logger

class IPMI(Debug):
    """Handles messages for IPMI requests"""

    implements(Iipmi)

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
            self._log_debug("perform_request, node_request: %s" % node_request)

            # Parse out the arguments for the IPMI action
            ipmi_request = node_request[5:].strip().split(" ", 1)
            self._log_debug("perform_request, ipmi_request: %s" % ipmi_request)

            if len(ipmi_request) != 2:
                return "Error: IPMI request must consist of [IP] [Command]"

            ipmi_ip = ipmi_request[0]
            ipmi_req_command = ipmi_request[1].lower()

            if ipmi_req_command == "on":                
                ipmi_command = "ipmitool -I lanplus -H {0} -U {1} -P {2} chassis power on" \
                                .format(ipmi_ip, self._user, self._pass)                
            elif ipmi_req_command == "off":
                ipmi_command = "ipmitool -I lanplus -H {0} -U {1} -P {2} chassis power soft" \
                                .format(ipmi_ip, self._user, self._pass)
            elif ipmi_req_command == "cycle":
                ipmi_command = "ipmitool -I lanplus -H {0} -U {1} -P {2} chassis power cycle" \
                                .format(ipmi_ip, self._user, self._pass)
            elif ipmi_req_command == "status":
                ipmi_command = "ipmitool -I lanplus -H {0} -U {1} -P {2} chassis status" \
                                .format(ipmi_ip, self._user, self._pass)
            else:
                return "Error: IPMI [IP] [Command], command must be on/off/cycle/status"

            self._log_debug("perform_request, IP: %s request: %s" %
                                (ipmi_ip, ipmi_command))

            # Run the command and get the response and error returned
            process = subprocess.Popen(ipmi_command, shell=True, stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE)
            response, error = process.communicate()

            if error:
                response = "{0}".format(error)

            self._log_debug("perform_request, IPMI response: %s" % response)

        except Exception as e:
            logger.exception(e)
            response = str(e)

        return response

    def _read_config(self):
        """Read in configuration values"""
        try:
            self._user = self._conf_reader._get_value_with_default(self.IPMI,
                                                                   self.USER,
                                                                   'admin')
            self._pass = self._conf_reader._get_value_with_default(self.IPMI,
                                                                   self.PASS,
                                                                   'admin')
            logger.info("IPMI Config: user: %s" % self._user)
        except Exception as e:
            logger.exception(e)
    
