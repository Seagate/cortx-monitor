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
        except OSError as os_err:
            return os_err.errno
        return self.nw_phy_link_state[carrier_indicator]
