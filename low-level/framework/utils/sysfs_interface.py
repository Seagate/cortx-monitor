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
Interface Module to Linux sysfs to interact with system devices,
drivers information and configuration.
"""


import os
from pathlib import Path

from framework.utils.utility import Utility
from framework.utils.conf_utils import SSPL_CONF, Conf

class SysFS(Utility):
    """Module which is responsible for fetching information
       internal to system such as SAS Port/SAS phy/network
       using /sys file system"""

    nw_phy_link_state = {'0':'DOWN', '1':'UP', 'unknown':'UNKNOWN'}

    def __init__(self):
        """init method"""
        super(SysFS, self).__init__()
        self.sysfs_base_path = SysFS.get_sysfs_base_path()
        self.sysfs = self.sysfs_base_path + "class/"
        self.cpu_online_fp = self.sysfs_base_path + "devices/system/cpu/online"
        self.sas_phy_dir_list = []
        self.phy_dir_dict = {}
        self.sas_phy_dir_path = {}

    def initialize(self):
        """Method for initialization.
           This iterates over /sys/class/sas_phy directory using listdir
           method of os module. And stores iterator to that path in the
           dictionary with key as dir_name.
           Ex: {"phy0": PosixPath('phy0')}"""
        try:
            self.sas_phy_dir_path = self.get_sys_dir_path('sas_phy')
            self.sas_phy_dir_list = os.listdir(self.sas_phy_dir_path)
            if self.sas_phy_dir_list:
                for phy_dir in self.sas_phy_dir_list:
                    absolute_phy_dir_path = \
                            os.path.join(self.sas_phy_dir_path, phy_dir)
                    self.phy_dir_dict[phy_dir] = Path(absolute_phy_dir_path)
        except OSError as os_error:
            return os_error.errno

    @classmethod
    def get_sysfs_base_path(cls):
        """Returns the sysfs base path. Ex: /sys."""
        sysfs_base_path = Conf.get(SSPL_CONF, "SYSTEM_INFORMATION>sysfs_base_path",
                            '/sys/')
        return sysfs_base_path

    def get_sys_dir_path(self, sys_dir_name):
        """Returns the complete sysfs directory path
           Ex: if arg is 'sas_phy', it will return /sys/class/sas_phy"""
        sys_dir_path = os.path.join(self.sysfs, sys_dir_name)
        return sys_dir_path

    def get_phy_negotiated_link_rate(self):
        """Iterates over the phy directory using the iterator and returns
           the dict with key as phy_name and value as negotiated linkrate
           {'phy0': <12G/Unknown/..>}"""
        phy_dir = {}
        # Get the iterator from the initialized global dictionary
        # And again iterates over respective directory to get the value
        # of negotiated linkrate from the 'negotiated linkrate' file
        # situated at /sys/class/sas_phy/<phy>/negotiated linkrate
        for phy_name, iterator in self.phy_dir_dict.items():
            for entry in iterator.iterdir():
                entry_str = str(entry)
                if 'negotiated_linkrate' in entry_str.lower() and entry.is_file():
                    link_rate = entry.read_text()
                    phy_dir[phy_name] = link_rate
        phy_dir = dict(sorted(phy_dir.items(),
                              key=lambda kv: int(kv[0].split(':')[1])))
        return phy_dir

    def convert_cpu_info_list(self, cpu_info):
        """Converts cpu info as read from file to a list of cpu indexes
        eg. '0-2,4,6-8' => [0,1,2,4,6,7,8]
        """
        # Split the string with comma
        cpu_info = cpu_info.split(',')
        cpu_list = []
        for item in cpu_info:
            # Split item with a hyphen if it is a range of indexes
            item = item.split('-')
            if len(item) == 2:
                # Item is a range
                num1 = int(item[0])
                num2 = int(item[1])
                # Append all indexes in that range
                for i in range(num1,num2+1):
                    cpu_list.append(i)
            elif len(item) == 1:
                # Item is a single index
                cpu_list.append(int(item[0]))
        return cpu_list

    def get_cpu_info(self):
        """Returns the cpus online after reading /sys/devices/system/cpu/online
        """
        cpu_info_path = Path(self.cpu_online_fp)
        # Read the text from /cpu/online file
        cpu_info = cpu_info_path.read_text()
        # Drop the \n character from the end of string
        cpu_info = cpu_info.rstrip('\n')
        # Convert the string to list of indexes
        cpu_list = self.convert_cpu_info_list(cpu_info)
        return cpu_list

    def fetch_nw_cable_status(self, nw_interface_path, interface):
        '''
           Gets the status of nw carrier cable from the path:
           /sys/class/net/<interface>/carrier. This file may have following
           values: <'0', '1', 'unknown'>. So, beased on its value, returns the
           status such as : <'DOWN', 'UP', 'UNKNOWN'> respectively.
        '''
        carrier_file_path = os.path.join(nw_interface_path, f'{interface}/carrier')

        carrier_indicator = 'unknown'
        try:
            with open(carrier_file_path) as cFile:
                carrier_indicator = cFile.read().strip()
            if carrier_indicator not in self.nw_phy_link_state.keys():
                carrier_indicator = 'unknown'
        except Exception:
            carrier_indicator = 'unknown'
        return self.nw_phy_link_state[carrier_indicator]

    def fetch_nw_operstate(self, interface):
        """
        Return the Operational Status of the Network Interface.

        Possible Values: <'UNKNOWN', 'NOTPRESENT", 'DOWN', 'LOWERLAYERDOWN',
                          'TESTING', 'DORMANT', 'UP'>
        """
        operstate_file_path = os.path.join(self.get_sys_dir_path('net'),
                                           interface, 'operstate')
        operstate = "UNKNOWN"
        try:
            if os.path.isfile(operstate_file_path):
                with open(operstate_file_path) as cFile:
                    operstate = cFile.read().strip().upper()
        except Exception as err:
            raise err
        return operstate

    def get_sas_host_list(self):
        """
            Return SAS host list from /sys/class/sas_host directory.

            eg: ['host1', 'host2']
        """
        sas_hosts = []
        try:
            host_dirpath = self.get_sys_dir_path('sas_host')
            sas_hosts = os.listdir(host_dirpath)
            sas_hosts = [host for host in sas_hosts
                         if 'host' in host]
        except Exception:
            return []
        return sas_hosts

    def get_sas_port_list(self, host=""):
        """
            Return a list of SAS ports.

            searches for ports from given host in /sys/class/sas_port
            directory if directory exists else return an empty list.
            eg: ['port-1:0', 'port-1:1', 'port-1:2', 'port-1:3']
        """
        sas_ports = []
        try:
            host_id = host.replace('host', '')
            port_dirpath = self.get_sys_dir_path('sas_port')
            sas_ports = os.listdir(port_dirpath)
            sas_ports = [port for port in sas_ports
                         if f'port-{host_id}' in port]
        except Exception:
            return []
        return sas_ports

    def get_sas_port_data(self, port_name):
        """
            Return SAS port data/info of given port.

            eg: Given input port-1:0 returns
                { "port_id":"sas_port-0",
                  "state":"running",
                  "sas_address":"0x500c0fff0a98b000"
                }
        """
        port_data = {}
        try:
            host_id, port_id = port_name.replace('port-', '').split(':')
            port_data_path = os.path.join(
                             self.get_sys_dir_path('sas_end_device'),
                             f'end_device-{host_id}:{port_id}',
                             f'device/target{host_id}:0:{port_id}',
                             f'{host_id}:0:{port_id}:0')
            with open(os.path.join(port_data_path, 'state')) as cFile:
                state = cFile.read().strip()

            with open(os.path.join(port_data_path, 'sas_address')) as cFile:
                sas_addr = cFile.read().strip()

            port_data = {
                    "port_id": f'sas_port-{port_id}',
                    "state": state,
                    "sas_address": sas_addr
                }
        except Exception:
            return {}
        return port_data

    def get_phy_list_for_port(self, port):
        """
            Return list of SAS phys under given port.

            eg: for given port-1:0 it might return
                [ 'phy-1:0', 'phy-1:1', 'phy-1:2', 'phy-1:3']
                returns an empty list if port-1:0 does not exist.
        """
        phys = []
        try:
            phy_list_dir = os.path.join(
                            self.get_sys_dir_path('sas_port'),
                            port, 'device')
            phys = os.listdir(phy_list_dir)
            phys = [phy for phy in phys if 'phy' in phy]
            phys.sort(key=lambda phy: int(phy.split(':')[1]))
        except Exception:
            return []
        return phys

    def get_sas_phy_data(self, phy):
        """
            Return SAS phy information.

            eg: for phy `phy-1:8` it might return
                {
                    "phy_id":"phy-1:8",
                    "state":"enabled",
                    "negotiated_linkrate":"12.0 Gbit"
                }
        """
        phy_data = {}
        try:
            phy_data_dir = os.path.join(
                            self.get_sys_dir_path('sas_phy'), phy)

            with open(os.path.join(phy_data_dir, 'enable')) as cFile:
                state = cFile.read().strip()
                state = "enabled" if state == '1' else "disabled"

            with open(os.path.join(phy_data_dir, 'negotiated_linkrate')) as cFile:
                n_link_rate = cFile.read().strip()

            phy_data = {
                "phy_id": phy,
                "state": state,
                "negotiated_linkrate": n_link_rate
            }
        except Exception:
            return {}
        return phy_data
