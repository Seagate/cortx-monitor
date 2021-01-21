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

import subprocess

import sys
import dbus
import psutil
from cortx.sspl.lowlevel.framework.utils.service_logging import logger
from cortx.utils.process import SimpleProcess

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
    def send_command(command: str, fail_on_error=True):
        # Note: This function uses subprocess to execute commands, scripts which are not possible to execute
        # through any python routines available. So its usage MUST be limited and used only when no other
        # alternative found.
        output, error, returncode = SimpleProcess(command).run()
        if returncode != 0:
            print("command '%s' failed with error\n%s" % (command, error))
            if fail_on_error:
                sys.exit(1)
            else:
                return str(error)
        return str(output)

    @staticmethod
    def call_script(script_dir: str, args: list):
        script_args_lst = [script_dir]+args
        is_error = subprocess.call(script_args_lst, shell=False)
        if is_error:
            sys.exit(1)

    @staticmethod
    def _initialize_dbus():
        """Initialization of dbus object."""
        system_bus = dbus.SystemBus()
        systemd1 = system_bus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
        dbus_manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')
        return dbus_manager

    @staticmethod
    def enable_disable_service(service, action = 'enable'):
        """Enable/Disable systemd services."""
        dbus_manager = Utility._initialize_dbus()
        if action == 'enable':
            dbus_manager.EnableUnitFiles([f'{service}'], False, True)
        else:
            dbus_manager.DisableUnitFiles([f'{service}'], False)
        dbus_manager.Reload()

    @staticmethod
    def systemctl_service_action(service, action = 'start'):
        """Start/Stop/Restart systemctl services."""
        dbus_manager = Utility._initialize_dbus()
        if action == 'start':
            dbus_manager.StartUnit(f'{service}', 'fail')
        elif action == 'stop':
            dbus_manager.StopUnit(f'{service}', 'fail')
        elif action == 'restart':
            dbus_manager.RestartUnit(f'{service}', 'fail')
        else:
            print(f"Invalid action: f'{service}' :Please provide an appropriate action name for the service.")

    @staticmethod
    def check_for_dep_rpms(rpm_list : list):
        for dep in rpm_list:
            name = Utility.send_command(f'rpm -q {dep}', fail_on_error=False)
            if "b''" in name:
                print(f"- Required rpm '{dep}' not installed, exiting")
                sys.exit(1)
    
    @staticmethod
    def check_for_active_processes(process_list : list):
        running_pl = [procObj.name() for procObj in psutil.process_iter() if procObj.name() in process_list ]
        for process in process_list:
            if(process not in running_pl):
                print(f"- Required process '{process}' not running, exiting")
                sys.exit(1)
