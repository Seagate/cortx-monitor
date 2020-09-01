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
