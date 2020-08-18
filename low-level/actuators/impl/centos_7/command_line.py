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
  Description:       Handles messages for command line requests
 ****************************************************************************
"""
import subprocess

from zope.interface import implementer
from actuators.Icommand_line import ICommandLine

from framework.base.debug import Debug
from framework.utils.service_logging import logger

@implementer(ICommandLine)
class CommandLine(Debug):
    """Handles messages for command line requests"""

    ACTUATOR_NAME = "CommandLine"

    # Section and keys in configuration file
    COMMANDLINE = ACTUATOR_NAME.upper()


    @staticmethod
    def name():
        """ @return: name of the module."""
        return CommandLine.ACTUATOR_NAME

    def __init__(self, conf_reader):
        super(CommandLine, self).__init__()

        # Read in the configuration values, possible future use
        #self._conf_reader = conf_reader
        #self._read_config()

        # Temporarily leave debugging on during beta release     
        self._set_debug(True)
        self._set_debug_persist(True)

    def perform_request(self, jsonMsg):
        """Performs the command line request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse out the login request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("perform_request, node_request: %s" % node_request)

            # Parse out the arguments for the command line action
            command_line_request = node_request[5:].strip().split(" ", 1)
            self._log_debug("perform_request, command line request: %s" % command_line_request)

            if len(command_line_request) == 0:
                return "Error: Command line request must consist of a command to perform"

            command_request = command_line_request[0].lower()

            if len(command_line_request) > 1:
                command_action = command_line_request[1].lower()
            else:
                command_action = "N/A"

            if command_request == "swap":
                if command_action == "on":
                    command = "sudo swapon -a"
                elif command_action == "off":
                    command = "sudo swapoff -a"
                else:
                    return "Error: SSPL SWAP [ON|OFF] only supported"

            elif command_request == "mount" or \
                 command_request == "umount":
                command = "sudo {}".format(node_request[5:].strip().lower())

            else:
                return "Error: SSPL [command] [action], command must be swap/mount/umount"

            self._log_debug("perform_request, command: %s" % command)

            # Run the command and get the response and error returned
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, 
                                       stderr=subprocess.PIPE)
            response, error = process.communicate()

            if error:
                response = "{0}".format(error)
            else:
                response = "Success"

            self._log_debug("perform_request, command response: %s" % response)

        except Exception as e:
            logger.exception(e)
            response = str(e)

        return response

    def _read_config(self):
        """Read in configuration values"""
        try:
            self._user = self._conf_reader._get_value_with_default(self.COMMANDLINE,
                                                                   self.USER,
                                                                   'admin')
            self._pass = self._conf_reader._get_value_with_default(self.COMMANDLINE,
                                                                   self.PASS,
                                                                   'admin')
            logger.info("CommandLine Config: user: %s" % self._user)
        except Exception as e:
            logger.exception(e)
    
