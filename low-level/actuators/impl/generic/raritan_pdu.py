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
  Description:       Handles messages to the Raritan PDU
 ****************************************************************************
"""
import serial
import paramiko
from functools import partial

from zope.interface import implementer
from actuators.Ipdu import IPDU

from framework.base.debug import Debug
from cortx.utils.log import Log as logger
from framework.utils.conf_utils import Conf, SSPL_CONF

@implementer(IPDU)
class RaritanPDU(Debug):
    """Handles request messages to the Raritan PDU"""

    ACTUATOR_NAME = "RaritanPDU"

    # Section and keys in configuration file
    RARITANPDU      = ACTUATOR_NAME.upper()
    USER            = 'user'
    PASS            = 'pass'
    COMM_PORT       = 'comm_port'
    IP_ADDR         = 'IP_addr'
    MAX_LOGIN_TRIES = 'max_login_attempts'

    MAX_CHARS       = 32767

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RaritanPDU.ACTUATOR_NAME

    def __init__(self, conf_reader):
        super(RaritanPDU, self).__init__()

        # Read in the configuration values
        self._conf_reader = conf_reader
        self._read_config()

    def perform_request(self, jsonMsg):
        """Performs the PDU request

        @return: The response string from the PDU
        """
        self._check_debug(jsonMsg)

        response = ""
        try:
            # Parse out the login request to perform
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug(f"perform_request, node_request: {node_request}")

            # Parse out the command to send to the PDU
            pdu_request = node_request[5:]
            self._log_debug(f"perform_request, pdu_request: {pdu_request}")

            # Create the serial port object and open the connection
            login_attempts = 0
            try:
                self._connection = serial.Serial(self._comm_port, 115200 , timeout=1)
            except Exception as ae:
                logger.info(f"Serial Port connection failure: {ae}")
                # Attempt network connection
                login_attempts = self._max_login_attempts

            # Send user/pass until max attempts has been reached
            while login_attempts < self._max_login_attempts:
                try:
                    if self._login_PDU() is True:
                        break
                except RuntimeError as re:
                    self._log_debug("Failed attempting to login to PDU via serial port: %s" % re)

                login_attempts += 1

            # If we exceeded login attempts then try the network approach
            if login_attempts == self._max_login_attempts:
                try:
                    self._log_debug("Attempting IP communications with PDU")

                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(self._ip_addr, port=22, username=self._user, password=self._pass)

                    # Execute the command in pdu_request show outlets details
                    (ssh_stdin, ssh_stdout, ssh_stderr) = client.exec_command(pdu_request + "\n", timeout=5)
                    ssh_stdin.write(pdu_request + "\n")
                    ssh_stdin.flush()

                    # Read in the results from the command
                    try:
                        for output in iter(partial(ssh_stdout.readline), ''):
                            #self._log_debug("output: %s" % str(output))
                            response += output
                    except Exception as ea:
                        self._log_debug("Reading from PDU completed")

                except Exception as e:
                    self._log_debug(f"Warning: Attempted IP connection to PDU: {e}")
                    return str(e)

                finally:
                    client.close()

            # Otherwise use the serial port
            else:
                self._log_debug("perform_request, Successfully logged into PDU")

                # Send the request and read the response via serial port
                response = self._send_request_read_response_serial(pdu_request)

                # Apply some validation to the response and retry as a safety net
                if self._validate_response(response) is False:
                    response = self._send_request_read_response_serial(pdu_request)

        except Exception as e:
            logger.exception(e)
            response = str(e)

        finally:
            self._logout_PDU()

        return response

    def _send_request_read_response_serial(self, pdu_request):
        """Sends the request and returns the string response"""
        self._connection.write(pdu_request + "\n")
        return self._connection.read(self.MAX_CHARS)

    def _login_PDU(self):
        """Sends the username and password to logon

        @return True if login was successful
        @raise RuntimeError: if an error occurs"""

        # Send the username and read the response
        response = self._send_request_read_response_serial(self._user)
        self._log_debug(f"_login_PDU, sent username: {self._user}")

        # Send over the password if it is requested
        if "Password:" in response:
             self._log_debug("_login_PDU, Password requested, sending")
             # Send the password
             response = self._send_request_read_response_serial(self._pass)
             # A successful login prompt is denoted by the '#'
             if "#" in response:
                 return True
             else:
                 raise RuntimeError("ERROR: authentication failure")

        # A successful login prompt is denoted by the '#' from previous session
        elif "#" in response:
            return True

        # Login attempt failed
        else:
            raise RuntimeError("no password prompt detected")

    def _logout_PDU(self):
        """Sends an exit command to properly logout and close connection"""
        try:
            # Attempt to properly exit the session
            self._connection.write("exit\n")
            # Close the connection
            self._connection.close()
        except Exception as e:
            self._log_debug('Error while logout {}'.format(e))

    def _validate_response(self, response):
        """Checks the response for the 'Available commands:' in response

        If the PDU returns a list of available commands then it did
            not recognize our command in which case we need to back
            out and try again as a safety net.

        @return: False if 'Available commands:' found in response otherwise True
        """
        if "Available commands:" in response:
            self._log_debug("Response shows list of available commands")
            # Reset the prompt by backspacing a large amount to put back on prompt
            for x in range(0, 500):
                self._connection.write("\b")
            return False
        return True

    def _read_config(self):
        """Read in configuration values"""
        try:
            self._user = Conf.get(SSPL_CONF, f"{self.RARITANPDU}>{self.USER}",'admin')
            self._pass = Conf.get(SSPL_CONF, f"{self.RARITANPDU}>{self.PASS}",'admin')
            self._comm_port = Conf.get(SSPL_CONF, f"{self.RARITANPDU}>{self.COMM_PORT}",'/dev/ttyACM0')
            self._ip_addr = Conf.get(SSPL_CONF, f"{self.RARITANPDU}>{self.IP_ADDR}",'172.16.1.222')
            self._max_login_attempts = int(Conf.get(SSPL_CONF, f"{self.RARITANPDU}>{self.MAX_LOGIN_TRIES}",5))

            logger.info("PDU Config: user: %s, Comm Port: %s, max login attempts: %s, IP: %s" %
                            (self._user, self._comm_port, self._max_login_attempts, self._ip_addr))
        except Exception as e:
            logger.exception(e)
