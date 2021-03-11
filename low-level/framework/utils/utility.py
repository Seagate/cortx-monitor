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
import subprocess
import os
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

def errno_to_str_mapping(err_no):
    """Convert numerical errno to its meaning."""
    try:
        err_info = os.strerror(err_no)
        return err_info
    except ValueError as err:
        raise Exception("map_errno_to_text, Unknown error number: %s" % err)
    except Exception as err:
        logger.error("map_errno_to_text errno to text mapping failed due to %s: %s " % err)
        return
