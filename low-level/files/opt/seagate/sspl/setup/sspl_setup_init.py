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
# - Check dependencies for consts.roles other than '<product>'
#################################################################

import os
import pwd
import errno

from cortx.sspl.bin.sspl_constants import file_store_config_path, roles
from cortx.utils.validator.v_service import ServiceV
from cortx.utils.validator.v_pkg import PkgV
from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.error import SetupError

class SSPLInit:
    """Init Setup Interface"""

    name = "init"

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

    HPI_PATH = '/tmp/dcs/hpi'
    MDADM_PATH = '/etc/mdadm.conf'

    def __init__(self, args : list):
        """ init methond for SSPL Setup Init Class"""
        self.args = args
        self.role = None
        self.dp = False

    def check_dependencies(self, role : str):
        # Check for dependency rpms and required processes active state based
        # on role
        if role == "ssu":
            try:
                PkgV().validate("rpms", self.SSU_DEPENDENCY_RPMS)
                ServiceV().validate("isrunning", self.SSU_REQUIRED_PROCESSES)
            except Exception:
                raise
        elif role == "vm" or role == "gw" or role == "cmu":
            try:
                # No dependency currently. Keeping this section as it may be
                # needed in future.
                PkgV().validate("isrunning", self.VM_DEPENDENCY_RPMS)
                # No processes to check in vm env
            except Exception:
                raise

    def get_uid(self, user_name : str) -> int:
        uid = -1
        try :
            uid =  pwd.getpwnam(user_name).pw_uid
        except KeyError :
            pass
        return uid

    def validate_args(self):
        if not self.args:
            raise SetupError(
                        errno.EINVAL,
                        "No arguments to init call.\n \
                        expected options : [-dp] [-r <ssu|gw|cmu|vm|cortx>]]"
                        )
        i = 0
        while i < len(self.args):
            if self.args[i] == '-dp':
                self.dp = True
            elif self.args[i] == '-r':
                i+=1
                if i == len(self.args):
                    raise SetupError(
                                errno.EINVAL, 
                                "No role provided with -r option")
                elif  self.args[i] not in roles:
                    raise SetupError(
                                errno.EINVAL,
                                "Provided role '%s' is not supported",
                                self.args[i])
                else:
                    self.role = self.args[i]
            else:
                raise SetupError(
                                errno.EINVAL, 
                                "Unknown option '%s'", self.args[i])
            i+=1

    def getval_from_ssplconf(self, varname : str) -> str:
        with open(file_store_config_path, mode='rt') as confile:
            for line in confile:
                if line.startswith(varname):
                    rets = line.split('=')[1]
                    if(rets.endswith('\n')):
                        rets = rets.replace('\n', '')
                    return rets
        return None

    def recursive_chown(self, path : str, user : str, grpid: int = -1):
        try:
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
        except OSError:
            raise

    def process(self):

        self.validate_args()

        if self.dp:
            # Extract the data path
            sspldp = self.getval_from_ssplconf('data_path')
            if not sspldp :
                raise SetupError(
                            errno.EINVAL, 
                            "Data Path Not set in sspl.conf")

            # Crete the directory and assign permissions
            try:
                os.makedirs(sspldp, mode=0o766, exist_ok=True)
            except OSError:
                raise
            self.recursive_chown(sspldp, 'sspl-ll')
        
        # Create /tmp/dcs/hpi if required. Not needed for '<product>' role
        if self.role != "cortx":
            try:
                os.makedirs(self.HPI_PATH, mode=0o777, exist_ok=True)
                zabbix_uid = self.get_uid('zabbix')
                if zabbix_uid != -1:
                    os.chown(self.HPI_PATH, zabbix_uid, -1)
            except OSError:
                raise

        # Check for sspl required processes and misc dependencies like
        # installation, etc based on 'role'
        if self.role:
            self.check_dependencies(self.role)
        
        # Create mdadm.conf to set ACL on it.
        with open(self.MDADM_PATH, 'a'):
            os.utime(self.MDADM_PATH)

        # TODO : verify for below replacement of setfacl command which
        #        gives rw permission to sspl-ll user for mdadm.conf file.
        os.chmod(self.MDADM_PATH, mode=0o666)
        sspl_ll_uid = self.get_uid('sspl-ll')
        if sspl_ll_uid == -1:
            raise SetupError(
                        errno.EINVAL, 
                        "No User Found with name : %s", 'sspl-ll')
        os.chown(self.MDADM_PATH, sspl_ll_uid, -1)
        