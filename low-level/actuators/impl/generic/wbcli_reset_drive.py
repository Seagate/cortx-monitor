# Copyright (c) 2001-2015 Seagate Technology LLC and/or its Affiliates
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
  Description:       Handles messages for power cycling drive requests
                    using the wbcli tool
 ****************************************************************************
"""
import os
import time
import subprocess

from zope.interface import implementer
from cortx.sspl.actuators.Ireset_drive import IResetDrive
from cortx.sspl.framework.base.debug import Debug
from cortx.sspl.framework.utils.service_logging import logger

@implementer(IResetDrive)
class WbcliResetDrive(Debug):
    """Handles request messages to power cycle drives using the wbcli tool"""

    ACTUATOR_NAME = "WbcliResetDrive"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return WbcliResetDrive.ACTUATOR_NAME

    def __init__(self):
        super(WbcliResetDrive, self).__init__()

    def perform_request(self, jsonMsg):
        """Performs the wbcli power cycle drive request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse out the node request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("perform_request, node_request: %s" % node_request)

            # Parse out the drive to power cycle on
            drive_request = node_request[13:].strip()
            self._log_debug("perform_request, drive to power cycle: %s" % drive_request)

            # Retrieve proper /dev/sg* number to use in command
            command = "ls /sys/class/enclosure/*/device/scsi_generic"
            scsi_dev, error = self._run_command(command)
            if error:
                return "Error: {0}".format(str(error))
            self._log_debug("perform_request, using scsi device: %s" % scsi_dev)

            # Get the serial number of the drive if the device name was used in command
            if drive_request.startswith("/"):
                command = "sudo /usr/sbin/hdparm -I {0} | grep 'Serial Number:'".format(drive_request)
                response, error = self._run_command(command)
                if error:
                    return "Error: {0}".format(str(error))

                serial_num = response.strip().split(" ")[-1]
            else:
                serial_num = drive_request
            self._log_debug("perform_request, drive serial number: %s" % serial_num)

            # Recursively grep through the drivemanager dir with the serial number and get the path
            command = "grep -R {0} /tmp/dcs/dmreport/* --exclude=/tmp/dcs/dmreport/drive_manager.json" \
                      .format(serial_num)
            response, error = self._run_command(command)
            if error:
                return "Error: {0}".format(str(error))

            # Parse out the drive number found in the drivemanager path to be used in the wbcli call
            drive_number = os.path.dirname(response).split("/")[-1]
            self._log_debug("perform_request, drive number: %s" % drive_number)

            # Turn the drive off
            command = "sudo /usr/sbin/fwdownloader -d /dev/{0} -wbcli 'poweroffdrive {1}'" \
                        .format(scsi_dev.strip(), drive_number)
            response, error = self._run_command(command)

            # Should be no error if command was successful
            if error:
                self._log_debug("perform_request, fwdownloader poweroffdrive error: %s, response: %s" %
                                (error, response))
                return "Error: {0}, Response: {1}".format(str(error), str(response))

            # Pause to allow time for powerdown
            time.sleep(10)

            # Turn the drive back on to complete reset
            command = "sudo /usr/sbin/fwdownloader -d /dev/{0} -wbcli 'powerondrive {1}'".format(scsi_dev.strip(), drive_number)
            response, error = self._run_command(command)

            # Pause to allow time for poweron
            time.sleep(45)

            # Should be no error if command was successful
            if error:
                self._log_debug("perform_request, fwdownloader powerondrive error: %s, response: %s" %
                                (error, response))
                return "Error: {0}, Response: {1}".format(str(error), str(response))

            response = "Successful"

        except Exception as e:
            logger.exception(e)
            response = "Error: {0}".format(str(e))

        return response

    def _run_command(self, command):
        """ Run the command and get the response and error returned"""

        self._log_debug("run_command, executing command: %s" % command)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()

        return response.rstrip('\n'), error.rstrip('\n')
