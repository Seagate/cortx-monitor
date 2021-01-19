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

import sys
import os
import subprocess
import pwd

sys.path.insert(0, '/opt/seagate/cortx/sspl/low-level/')

from framework.base.sspl_constants import file_store_config_path, roles
from files.opt.seagate.sspl.setup.sspl_setup import Cmd as SSPLSetup

import psutil
import rpm 

class Init:
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
        self.args = args
        self.role = None
        self.ts = rpm.TransactionSet()

    def usage(self):
        sys.stderr.write(
            f"{self.name} [check|create [-dp] [-r <ssu|gw|cmu|vm|cortx>]]\n"
            "create options:\n"
            "\t -dp Create configured datapath\n"
            "\t -r  Role to be configured on the current node\n"
            )
        sys.exit(1)

    def check_for_dep_rpms(self, rpm_list : list):
        for dep in rpm_list:
            mi = self.ts.dbMatch('name', dep)
            ispresent = False
            for k in mi:
                if(k['name'] == dep):
                    ispresent = True
            if not ispresent:
                sys.stderr.write(f"- Required rpm '{dep}' not installed, exiting\n")
                sys.exit(1)
    
    def check_for_active_processes(self, process_list : list):
        running_pl = [procObj.name() for procObj in psutil.process_iter() if procObj.name() in process_list ]
        for process in process_list:
            if(process not in running_pl):
                print(f"- Required process '{process}' not running, exiting")
                sys.exit(1)

    def check_dependencies(self, role : str):
        # Check for dependency rpms and required processes active state based on role
        if role == "ssu":
            print(f"Checking for dependency rpms for role '{role}'")
            self.check_for_dep_rpms(self.SSU_DEPENDENCY_RPMS)
            print(f"Checking for required processes running state for role '{role}'")
            self.check_for_active_processes(self.SSU_REQUIRED_PROCESSES)
        elif role == "vm" or role == "gw" or role == "cmu":
            print(f"Checking for dependency rpms for role '{role}'")
            # No dependency currently. Keeping this section as it may be
            # needed in future.
            self.check_for_dep_rpms(self.VM_DEPENDENCY_RPMS)
            # No processes to check in vm env
        else:
            print(f"No rpm or process dependencies set, to check for supplied role {role}, skipping checks.\n")

    def get_uid(self, proc_name : str) -> int:
        uid = -1
        try :
            uid = pwd.getpwnam(proc_name).pw_uid
        except KeyError :
            print(f"No such User: {proc_name}")
        return uid

    def process(self):
        if not self.args:
            self.usage()

        i = 0
        while i < len(self.args):
            if self.args[i] == '-dp':
                # Extract the data path
                sspldp = ''
                with open(file_store_config_path, mode='rt') as confile:
                    for line in confile:
                        if line.find('data_path') != -1:
                            sspldp = line.split('=')[1]
                            break
                # Crete the directory and assign permissions
                try:
                    os.makedirs(sspldp, mode=0o766, exist_ok=True)
                    sspl_ll_uid = self.get_uid('sspl-ll')
                    if sspl_ll_uid == -1:
                        sys.exit(1)
                    os.chown(sspldp, sspl_ll_uid, -1)
                    for root, dirs, files in os.walk(sspldp):
                        for item in dirs:
                            os.chown(os.path.join(root, item), sspl_ll_uid, -1)
                        for item in files:
                            os.chown(os.path.join(root, item), sspl_ll_uid, -1)
                except OSError as error:
                    print(error)
                    sys.exit(1)

            elif self.args[i] == '-r':
                i+=1
                if i>= len(self.args) or self.args[i] not in roles:
                    self.usage()
                else:
                    self.role = self.args[i]
            else:
                self.usage()
            i+=1
        
        # Create /tmp/dcs/hpi if required. Not needed for '<product>' role
        if self.role != "cortx":
            try:
                os.makedirs(self.HPI_PATH, mode=0o777, exist_ok=True)
                zabbix_uid = self.get_uid('zabbix')
                if zabbix_uid != -1:
                    os.chown(self.HPI_PATH, zabbix_uid, -1)
            except OSError as error:
                print(error)

        # Check for sspl required processes and misc dependencies like installation, etc based on 'role'
        if self.role:
            self.check_dependencies(self.role)
        
        # Create mdadm.conf to set ACL on it.
        with open(self.MDADM_PATH, 'a'):
            os.utime(self.MDADM_PATH)

        # TODO : verify or find accurate replacement for setfacl command which
        #        gives rw permission to sspl-ll user for mdadm.conf file.
        # SSPLSetup._send_command('setfacl -m u:sspl-ll:rw /etc/mdadm.conf')
        os.chmod(self.MDADM_PATH, mode=0o666)
        sspl_ll_uid = self.get_uid('sspl-ll')
        if sspl_ll_uid == -1:
            sys.exit(1)
        os.chown(self.MDADM_PATH, sspl_ll_uid, -1)
        
if __name__ == "__main__":
    ic = Init(sys.argv[1:])
    ic.process()
