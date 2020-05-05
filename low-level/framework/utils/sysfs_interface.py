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

"""
Factory module which returns instance of specific tool/utility class.
"""

class ToolFactory(object):
    """"Returns instance of a specific Tool class from the factory"""

    def __init__(self):
        """init method"""
        self._instance = None

    def get_instance(self, utility_name):
        """Returns the instance of the utility by iterating globals
           dictionary"""

        if self._instance is None:
            for key, _ in globals().items():
                if key.lower() == utility_name.lower():
                    self._instance = globals()[key]()
                    break
        return self._instance
