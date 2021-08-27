# Copyright (c) 2019-2020 Seagate Technology LLC and/or its Affiliates
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

from cortx.utils.process import SimpleProcess


class SystemInfo:
    """ Interface class to retrieve system's hardware related info using 'dmidecode' command."""

    DMIDECODE = "sudo /sbin/dmidecode"

    def __init__(self):
        """Init method."""
        super(SystemInfo, self).__init__()
        self.resource_code_map = {
            "cpu" : 4,
            "psu" : 39
        }

    def get_system_info(self, resource):
        cmd = self.DMIDECODE + " -t " + str(self.resource_code_map[resource])
        output, err, rc = SimpleProcess(cmd).run()
        return output, err, rc

