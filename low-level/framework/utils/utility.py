# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
Base class for all the Utility implementation
"""

import re
import os
import time
import calendar
import socket
import subprocess
from framework.utils.service_logging import logger


class Utility(object):
    """Base class for all the utilities
    """
    def __init__(self):
        """Init method"""
        super(Utility, self).__init__()

    def execute_cmd(self, command=[]):
        """Executes action using python subprocess module
           and returns the output
           1. output of the command in byte
           2. return_code).
        """
        #TODO Handle exception at caller side
        process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,\
                                    stderr=subprocess.PIPE)
        _result, _err = process.communicate()
        return _result, _err, process.returncode

    def is_env_vm(self):
        """
        Returns true if VM env, false otherwise
        """
        is_vm = True
        CMD = "facter is_virtual"
        try:
            subout = subprocess.Popen(CMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = subout.stdout.readlines()
            if result == [] or result == "":
                logger.warning("Not able to read whether env is vm or not, assuming VM env.")
            else:
                if 'false' in result[0].decode():
                    is_vm = False
        except Exception as e:
            logger.warning("Error while reading whether env is vm or not, assuming VM env : {e}")
        return is_vm

    def get_machine_id(self):
        """
        Returns machine-id from /etc/machine-id.
        """
        with open("/etc/machine-id") as f:
            return f.read().strip("\n")

    def get_os(self):
        """
        Returns os name({ID}{VERSION_ID}) from /etc/os-release.
        """
        with open("/etc/os-release") as f:
            os_release = f.read()
            os_id = re.findall('^ID=(.*)\n', os_release, flags=re.MULTILINE)
            os_version_id = re.findall('^VERSION_ID=(.*)\n', os_release, flags=re.MULTILINE)
            if os_id and os_version_id:
                return "".join([_.strip('"') for _ in os_id+os_version_id])
            else:
                return None

    def get_epoch_time(self, date, _time):
        timestamp_format = '%m/%d/%Y %H:%M:%S'
        timestamp = time.strptime('{} {}'.format(date, _time), timestamp_format)
        return str(int(calendar.timegm(timestamp)))

    def create_file(self, path):
        """Create a file at specified path."""
        dir = path[:path.rindex("/")]
        if not os.path.exists(dir):
            os.makedirs(dir)
        if not os.path.exists(path):
            file = open(path, "w+")
            file.close()

    def read_raw_filedata(self, file):
        """Reads the data from the file and returns it as a string."""
        if not os.path.isfile(file):
            return str(None)

        with open (file, "r") as datafile:
            return str(datafile.read().replace('\n', ''))

    def get_hostname(self):
        try:
            logger.debug(f"Fetched hostname:{socket.getfqdn()} using getfqdn().")
            return socket.getfqdn()
        except Exception as ex:
            logger.error(f"Got exception: {ex} when trying to get hostname using getfqdn().")
        try:
            from subprocess import run, PIPE
            from re import findall

            IP_CMD = "ip -f inet addr show scope global up | grep inet"
            IP_REGEX = b'\\b(\\d{1,3}(?:\\.\d{1,3}){3})/\d{1,2}\\b'

            ip_out = run(IP_CMD, stdout=PIPE, shell=True, check=True)
            ip_list = findall(IP_REGEX, ip_out.stdout)
            if ip_list:
                logger.debug(f"Fetched hostname:{ip_list[0]} using ip addr command.")
                return ip_list[0]
        except Exception as ex:
            logger.error(f"Got exception: {ex} when trying to get hostname"
                    " using ip addr command.")

        # Ultimate fallback, when we are completely out of options
        logger.debug("Returning hostname:'localhost'.")
        return "localhost"