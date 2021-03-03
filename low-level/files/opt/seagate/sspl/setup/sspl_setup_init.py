#!/bin/env python3

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

#################################################################
# This script performs following operations.
# - Creates datapath as defined in /etc/sspl.conf
# - Check dependencies for roles other than '<product>'
#################################################################

import os
import pwd
import errno

from framework.base.sspl_constants import (sspl_config_path,
                                           setups,
                                           HPI_PATH,
                                           MDADM_PATH,
                                           SSPL_CONFIG_INDEX,
                                           GLOBAL_CONFIG_INDEX)
from cortx.utils.validator.v_service import ServiceV
from cortx.utils.validator.v_pkg import PkgV
from .setup_error import SetupError
from cortx.utils.conf_store import Conf


class SSPLInit:

    """Creates Data Path and checks for process and
       rpm dependencies based on role.
    """

    name = "SSPL Init"

    SSU_DEPENDENCY_RPMS = [
                "sg3_utils",
                "gemhpi",
                "pull_sea_logs",
                "python-hpi",
                "zabbix-agent-lib",
                "zabbix-api-gescheit",
                "zabbix-xrtx-lib",
                "python-openhpi-baselib",
                "zabbix-collector",
    ]

    SSU_REQUIRED_PROCESSES = [
                    "openhpid",
                    "dcs-collectord",
    ]

    VM_DEPENDENCY_RPMS = []

    def __init__(self):
        """initial variables and ConfStor setup."""
        self.role = None
        self.dp = True
        # Load sspl and global configs
        Conf.load(SSPL_CONFIG_INDEX, sspl_config_path)
        global_config_url = Conf.get(
            SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_copy_url")
        Conf.load(GLOBAL_CONFIG_INDEX, global_config_url)
        self.role = Conf.get(GLOBAL_CONFIG_INDEX, 'release>setup')

    def check_dependencies(self):
        # Check for dependency rpms and required processes active state based
        # on role
        if self.role == "ssu":
            PkgV().validate("rpms", self.SSU_DEPENDENCY_RPMS)
            ServiceV().validate("isrunning", self.SSU_REQUIRED_PROCESSES, is_process=True)
        elif self.role == "vm" or self.role == "gw" or self.role == "cmu":
            # No dependency currently. Keeping this section as it may be
            # needed in future.
            PkgV().validate("rpms", self.VM_DEPENDENCY_RPMS)
            # No processes to check in vm env

    def get_uid(self, user_name : str) -> int:
        uid = -1
        try :
            uid =  pwd.getpwnam(user_name).pw_uid
        except KeyError :
            pass
        return uid

    def recursive_chown(self, path : str, user : str, grpid: int = -1):
        uid = self.get_uid(user)
        if uid == -1:
            raise SetupError(
                        errno.EINVAL,
                        "No User Found with name : %s", user)
        os.chown(path, uid, grpid)
        for root, dirs, files in os.walk(path):
            for item in dirs:
                os.chown(os.path.join(root, item), uid, grpid)
            for item in files:
                os.chown(os.path.join(root, item), uid, grpid)

    def process(self):
        if self.dp:
            # Extract the data path
            sspldp = Conf.get(SSPL_CONFIG_INDEX,
                              'SYSTEM_INFORMATION>data_path')
            if not sspldp:
                raise SetupError(
                    errno.EINVAL,
                    "Data Path Not set in %s"
                    % sspl_config_path)

            # Crete the directory and assign permissions
            os.makedirs(sspldp, mode=0o766, exist_ok=True)
            self.recursive_chown(sspldp, 'sspl-ll')

        # Create /tmp/dcs/hpi if required. Not needed for '<product>' role
        if self.role != "cortx":
            os.makedirs(HPI_PATH, mode=0o777, exist_ok=True)
            zabbix_uid = self.get_uid('zabbix')
            if zabbix_uid != -1:
                os.chown(HPI_PATH, zabbix_uid, -1)

        # Check for sspl required processes and misc dependencies like
        # installation, etc based on 'role'
        if self.role:
            self.check_dependencies()

        # Create mdadm.conf to set ACL on it.
        with open(MDADM_PATH, 'a'):
            os.utime(MDADM_PATH)

        # TODO : verify for below replacement of setfacl command which
        #        gives rw permission to sspl-ll user for mdadm.conf file.
        os.chmod(MDADM_PATH, mode=0o666)
        sspl_ll_uid = self.get_uid('sspl-ll')
        if sspl_ll_uid == -1:
            raise SetupError(
                        errno.EINVAL,
                        "No User Found with name : %s", 'sspl-ll')
        os.chown(MDADM_PATH, sspl_ll_uid, -1)
