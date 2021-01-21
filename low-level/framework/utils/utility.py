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

