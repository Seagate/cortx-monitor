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
import pwd
import grp
import errno
import socket
from cortx.utils.conf_store import Conf
from cortx.utils.conf_store.error import ConfError
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

    @staticmethod
    def get_machine_id():
        """
        Returns machine-id from /etc/machine-id.
        """
        machine_id = None
        with open("/etc/machine-id") as f:
            machine_id = f.read().strip()
        if not machine_id:
            raise Exception("Unable to get machine id from host '%s'." % socket.getfqdn())
        return machine_id

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

    @staticmethod
    def get_uid(user_name):
        """Get user id."""
        uid = -1
        try :
            uid = pwd.getpwnam(user_name).pw_uid
        except KeyError:
            pass
        return uid

    @staticmethod
    def get_gid(user_name):
        """Get group id."""
        gid = -1
        try :
            gid = grp.getgrnam(user_name).gr_gid
        except KeyError:
            pass
        return gid

    @staticmethod
    def get_config_value(index, key):
        value = Conf.get(index, key)
        if not value:
            raise ConfError(errno.EINVAL, "Config validation failure. \
                No value found for key: '%s' in input config.", key)
        return value

    @staticmethod
    def replace_expr(filename:str, key, new_str:str):
        """The function helps to replace the expression provided as key
        with new string in the file provided in filename OR it inserts
        the new string at given line as a key in the provided file.
        """
        with open(filename, 'r+') as f:
            lines = f.readlines()
            if isinstance(key, str):
                for i, line in enumerate(lines):
                    if re.search(key, line):
                        lines[i] = re.sub(key, new_str, lines[i])
            elif isinstance(key, int):
                if not re.search(new_str, lines[key]):
                    lines.insert(key, new_str)
            else:
                raise Exception("Key data type : '%s', should be string or int" % type(key))
            f.seek(0)
            for line in lines:
                f.write(line)

    @staticmethod
    def set_ownership_recursively(root_dir, uid, gid):
        """Set ownership recursively."""
        os.chown(root_dir, uid, gid)
        for base, dirs, files in os.walk(root_dir):
            for _dir in dirs:
                os.chown(os.path.join(base, _dir), uid, gid)
            for file in files:
                os.chown(os.path.join(base, file), uid, gid)

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

