"""
Interface Module to Linux sysfs to interact with system devices,
drivers information and configuration.
"""


import os
from pathlib import Path

from framework.utils.utility import Utility

class SysFS(Utility):
    """Module which is responsible for fetching information
       internal to system such as SAS Port/SAS phy/network
       using /sys file system"""

    sysfs = "/sys/class/"
    cpu_online_fp = "/sys/devices/system/cpu/online"
    nw_phy_link_state = {'0':'DOWN', '1':'UP', 'unknown':'UNKNOWN'}

    def __init__(self):
        """init method"""
        super(SysFS, self).__init__()
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

