"""
 ****************************************************************************
 Filename:          smartctl.py
 Description:       Handles messages for drive smart requests using smartctl tool
 Creation Date:     16/03/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************

sample internal JSON reqeust to query smartctl tool:
    actuator_request_type": {
        "node_controller": {
            "node_request": SMARTCTL: GET_SERIAL <drive-path>
            }
        }
"""

import subprocess

from zope.interface import implementer

from framework.base.debug import Debug
from framework.utils.service_logging import logger
from actuators.Ismartctl import ISmartctl


@implementer(ISmartctl)
class Smartctl(Debug):
    """Handles messages for requests using smartctl tool"""


    ACTUATOR_NAME = "Smartctl"
    VALID_REQUESTS = ["GET_SERIAL"]

    @staticmethod
    def name():
        """ @return: name of the module."""
        return Smartctl.ACTUATOR_NAME

    def __init__(self):
        super(Smartctl, self).__init__()

    def perform_request(self, json_msg):
        """executes request to fetch the serial number of the drive

        @return: The response string from performing the request
        """
        self._check_debug(json_msg)

        response = "N/A"
        # Parse out the node request to perform
        node_request = json_msg.get("actuator_request_type").get("node_controller").get("node_request")
        self._log_debug("perform_request, node_request: %s" % node_request)

        # Parse out the drive to power cycle on
        # node_request is "SMARTCTL: GET_SERIAL <drive-path>"
        request_type = node_request[10:].strip().split(" ")[0]
        drive_path = node_request[21:].strip()
        self._log_debug("perform_request, smart request: %s" % request_type)

        if self._validate_requests(request_type):
            if request_type == "GET_SERIAL":
                # Build the desired command using smartctl tool
                command = "sudo /usr/sbin/smartctl -i {0}".format(drive_path)
                response = self._run_command(command)

                # parse out the response in order to get 'Serial Number: <serial_number>' this as output
                if "Error" not in response:
                    smart_field_list = response.split("\n")
                    for field in smart_field_list:
                        if "serial" in field.lower():
                            response = field
        else:
            response = "Error: Invalid request"
        return response

    def _run_command(self, command):
        """executes smartctl command for particular request"""
        response = None

        try:
            self._log_debug("_run_command, executing command: %s" % command)
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            res = process.communicate()
            response = ''.join(res)
            # If an error exists stop here and return the response
            if process.returncode != 0:
                err_response = response.split('\n')[3]
                err = f"Error:{err_response}"
                return err
        except Exception as exc:
            logger.exception(exc)
            response = f"Error:{exc}"

        return response

    def _validate_requests(self, request_type):
        """ Validates request for this actuator """
        response = ""
        self._log_debug("_validate_requests, smartctl_request %s" % request_type)
        if request_type not in self.VALID_REQUESTS:
            logger.error("_validate_request, %s is not a valid request" % request_type)
            return False
        return True

    def _check_serial_number(self, drive_request):
        """checks serial_number pass in --smart cmd  matched with any drive present on system """
        #get all drives present on system
        command = "sudo /usr/sbin/smartctl --scan"
        response = self._run_command(command)
        drive_list = response.strip().split("\n")
        for drive in drive_list:
            drive_path = drive[:9]
            #get serial number of drive.
            command =  "sudo /usr/sbin/smartctl -i {0} | grep Serial".format(drive_path)
            response = self._run_command(command)
            serial_number = response[14:].strip()
            if drive_request == serial_number:
                return True
        return False
