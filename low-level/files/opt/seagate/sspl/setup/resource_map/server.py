#!/bin/python3

# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com

"""
 ***************************************************************************
  Description: ServerMap class provides resource map and related information
               like health, manifest, etc,.
 ***************************************************************************
"""

import errno
import time
import re
import psutil
from pathlib import Path
from framework.utils.conf_utils import (Conf, SSPL_CONF)
from resource_map import ResourceMap
from error import ResourceMapError


class ServerMap(ResourceMap):
    """Provides server resource related information."""

    name = "server"

    def __init__(self):
        """Initialize server"""
        super().__init__()
        self.sysfs_base_path = self.get_sysfs_base_path()
        self.cpu_path = self.sysfs_base_path + "devices/system/cpu/"
        self.server_frus = {
            'cpu': self.get_cpu_info
        }

    def get_health_info(self, rpath):
        """
        Get health information of fru in given resource id

        rpath: Resource id (Example: nodes[0]>compute[0]>hw>disks)
        """
        info = {}
        fru_found = False
        nodes = rpath.strip().split(">")
        leaf_node, _ = self.get_node_details(nodes[-1])
        if leaf_node == "compute":
            for fru in self.server_frus:
                info.update({fru: self.server_frus[fru]()})
            info["last_updated"] = int(time.time())
            fru_found = True
        else:
            fru = None
            for node in nodes:
                fru, _ = self.get_node_details(node)
                if self.server_frus.get(fru):
                    fru_found = True
                    info = self.server_frus[fru]()
                    break
        if not fru_found:
            raise ResourceMapError(
                errno.EINVAL,
                "Health provider doesn't have support for'{rpath}'.")
        return info

    @staticmethod
    def get_node_details(node):
        """
        Parse node information and returns left string and instance.

        Example
            "storage"    -> ("storage", "*")
            "storage[0]" -> ("storage", "0")
        """
        res = re.search(r"(\w+)\[([\d]+)\]|(\w+)", node)
        inst = res.groups()[1] if res.groups()[1] else "*"
        node = res.groups()[0] if res.groups()[1] else res.groups()[2]
        return node, inst

    @classmethod
    def get_sysfs_base_path(cls):
        """Returns the sysfs base path. Ex: /sys."""
        sysfs_base_path = Conf.get(SSPL_CONF,
                                   "SYSTEM_INFORMATION>sysfs_base_path", '/sys/')
        return sysfs_base_path

    @staticmethod
    def get_data_template(uid, is_fru: bool):
        """Returns health template."""
        return {
            "uid": uid,
            "fru": str(is_fru).lower(),
            "last_updated": int(time.time()),
            "health": {
                "status": "",
                "description": "",
                "recommendation": "",
                "specifics": []
            }
        }

    @staticmethod
    def set_health_data(health_data: dict, status, description=None,
                        recommendation=None, specification=None):
        """Sets health attributes for a component."""
        good_state = (status == "OK")
        if not description:
            description = "%s %s in good health" % (
                health_data.get("uid"),
                'is' if good_state else 'is not')
        if not recommendation:
            recommendation = 'None' if good_state\
                             else "Fault detected, please contact Seagate support."

        health_data["health"].update({
            "status": status,
            "description": description,
            "recommendation": recommendation,
            "specifics": specification
        })

    def get_cpu_info(self):
        """Update and return CPU information in specific format."""
        cpu_data = []
        cpu_present = self.get_cpu_list("present")
        cpu_online = self.get_cpu_list("online")
        cpu_usage = psutil.cpu_percent(interval=None, percpu=True)
        cpu_usage_dict = dict(zip(cpu_online, cpu_usage))

        for cpu_id in range(0, len(cpu_present)):
            uid = f"cpu_{cpu_id}"
            cpu_dict = self.get_data_template(uid, False)
            online_status = "Online" if cpu_id in cpu_online else "Offline"
            health_status = "OK" if online_status == "Online" else "Fault"
            usage = "NA" if health_status == "Fault" \
                else cpu_usage_dict[cpu_id]
            specification = [
                {
                    "cpu_usage": usage,
                    "state": online_status
                }
            ]
            self.set_health_data(cpu_dict, status=health_status,
                                 specification=specification)
            cpu_data.append(cpu_dict)
        return cpu_data

    def get_cpu_list(self, mode):
        """Returns the cpus present after reading."""
        cpu_info_path = Path(self.cpu_path+mode)
        # Read the text from /cpu/online file
        cpu_info = cpu_info_path.read_text()
        # Drop the \n character from the end of string
        cpu_info = cpu_info.rstrip('\n')
        # Convert the string to list of indexes
        cpu_list = self.convert_cpu_info_list(cpu_info)
        return cpu_list

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
                for i in range(num1, num2+1):
                    cpu_list.append(i)
            elif len(item) == 1:
                # Item is a single index
                cpu_list.append(int(item[0]))
        return cpu_list


# if __name__ == "__main__":
#     server = ServerMap()
#     health_data = server.get_health_info(rpath="nodes[0]>compute[0]>hw>cpu")
#     print(health_data)
