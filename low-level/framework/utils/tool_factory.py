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
Factory module which returns instance of specific tool/utility class.
"""

from cortx.sspl.framework.utils.sysfs_interface import *
from cortx.sspl.framework.utils.procfs_interface import *

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
