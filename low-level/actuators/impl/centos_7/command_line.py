"""
 ****************************************************************************
 Filename:          command_line.py
 Description:       Handles messages for command line requests
 Creation Date:     06/05/2016
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
from actuators.Icommand_line import ICommandLine

from framework.base.debug import Debug
from framework.utils.service_logging import logger

class CommandLine(Debug):
    """Handles messages for command line requests"""

    implements(ICommandLine)

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
    
