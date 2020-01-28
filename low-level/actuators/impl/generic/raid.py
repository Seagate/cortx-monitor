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

from zope.interface import implementer
from actuators.Iraid import IRAIDactuator

from framework.base.debug import Debug
from framework.utils.service_logging import logger

@implementer(IRAIDactuator)
class RAIDactuator(Debug):
    """Handles request messages for RAID requests"""


    ACTUATOR_NAME = "RAIDactuator"
    SUCCESS_MSG = "Success"
    @staticmethod
    def name():
        """ @return: name of the module."""
        return RAIDactuator.ACTUATOR_NAME

    def __init__(self):
        super(RAIDactuator, self).__init__()
        self._conf_command = "sudo /usr/sbin/mdadm --detail --scan > /etc/mdadm.conf"

    def perform_request(self, jsonMsg):
        """Performs the RAID request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse out the node request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("perform_request, node_request: %s" % node_request)

            # Parse out the arguments for the RAID action
            raid_request = node_request[5:].strip()
            self._log_debug("perform_request, raid_request: %s" % raid_request)

            # The 'mdadm' command has two modes of execution.
            # 1. options: These start with '--' such as '--assemble'
            # 2. device: Here arguments are device names i.e. /dev/... as first argument

            if raid_request.startswith("/dev"):
                command = "sudo /usr/sbin/mdadm {0}".format(raid_request)
            else:
                command = "sudo /usr/sbin/mdadm --{0}".format(raid_request)

            self._log_debug("perform_request, executing RAID command: %s" % command)

            # Run the command and get the response and error returned
            process = subprocess.Popen(command.split(), shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            output, err = process.communicate()

            # /etc/mdadm.conf needs to be created/updated after each operation to keep track of state.
            if raid_request.find("create") >= 0 and process.returncode == 0:
                self._log_debug("perform_request, executing RAID command: %s" % self._conf_command)
                subprocess.Popen(self._conf_command, shell=True)

            if process.returncode != 0:
                response = f"Error:{err}"
            else:
                response = RAIDactuator.SUCCESS_MSG

            self._log_debug("perform_request, RAID response: %s return code: %d" \
            % (response + ":{}".format(output or err), process.returncode))

        except Exception as e:
            logger.exception(e)
            response = f"Error:{err}"

        return response
