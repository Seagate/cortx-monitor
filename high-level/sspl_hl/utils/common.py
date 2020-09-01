# Copyright (c) 2017 Seagate Technology LLC and/or its Affiliates
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
Contain the common utils and functions
"""

import subprocess
import datetime


def execute_shell(shell_cmd):
    """
    Execute the command in shell
    """
    return subprocess.check_output(
        shell_cmd,
        stderr=subprocess.PIPE,
        shell=True
    )


def get_curr_datetime_str():
    """
        Return current date time in yyyymmddhhmmss format.
    """
    date_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return date_time


class Components(object):
    """Components that lists all the components in the cluster for which
    we need to grant access. In the actual Linux enc these will be mapped
    to groups.
    """

    I_NONE = 0
    I_ROOT = 1
    I_FS_TOOLS = 2
    I_RAS = 3
    I_S3 = 4
    I_APACHE = 5
    I_FS_CLI = 6
    I_FS_GUI = 7
    I_SEASTREAM = 8

    NONE = ''
    ROOT = 'root'
    FS_TOOLS = 'fs-tools'
    RAS = 'ras'
    S3 = 's3'
    APACHE = 'apache'
    FS_CLI = 'fs-cli'
    FS_GUI = 'fs-gui'
    SEASTREAM = 'seastream'

    def __init__(self):
        self.components = {Components.FS_TOOLS: Components.I_FS_TOOLS,
                           Components.RAS:  Components.I_RAS,
                           Components.S3: Components.I_S3,
                           Components.ROOT: Components.I_ROOT,
                           Components.APACHE: Components.I_APACHE,
                           Components.FS_CLI: Components.I_FS_CLI,
                           Components.FS_GUI: Components.I_FS_GUI,
                           Components.SEASTREAM: Components.I_SEASTREAM
                           }

    def get_component_code(self, component):
        """returns the component code"""
        return self.components.get(component, None)
