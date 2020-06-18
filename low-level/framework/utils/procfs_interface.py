"""
Interface Module to Linux procfs to interact with system devices,
drivers information and configuration.
"""
import os

from pathlib import Path
from framework.utils.utility import Utility


class ProcFS(Utility):
    """Module which is responsible for fetching information internal
       to system such as total RAM etc using /proc file system"""

    procfs = "/proc/"

    def __init__(self):
        """init method"""
        super(ProcFS, self).__init__()

    def get_proc_memory(self, proc_file_name):
        """Return the complete directory path for memory info file
           i.e. if arg is meminfo, it will return /proc/meminfo"""

        proc_mem = os.path.join(self.procfs, proc_file_name)
        proc_mempath = Path(proc_mem)
        return proc_mempath
