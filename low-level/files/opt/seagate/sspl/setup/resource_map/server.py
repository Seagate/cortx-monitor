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


import time
import re
import errno
from framework.utils.ipmi_client import IpmiFactory
from framework.base import sspl_constants

import errno
import time
import psutil
from pathlib import Path
from framework.utils.tool_factory import ToolFactory
from resource_map import ResourceMap
from error import ResourceMapError
from framework.base.sspl_constants import CPU_PATH


class ServerMap(ResourceMap):
    """ServerMap class provides resource map and related information
    like health, manifest, etc,.
    """

    name = "server"

    def __init__(self):
        """Initialize server"""
        super().__init__()
        self.sysfs = ToolFactory().get_instance('sysfs')
        self.sysfs.initialize()
        self.sysfs_base_path = self.sysfs.get_sysfs_base_path()
        self.cpu_path = self.sysfs_base_path + CPU_PATH
        self.server_frus = {
            'cpu': self.get_cpu_info,
            'platform_sensors': self.get_platform_sensors_info,
        }
        self._ipmi = IpmiFactory().get_implementor("ipmitool")
        self.platform_sensor_list = ['Temperature', 'Voltage', 'Current']

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
                f"Health provider doesn't have support for'{rpath}'.")
        return info

    @staticmethod
    def set_health_data(health_data: dict, status, description=None,
                        recommendation=None, specifics=None):
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
            "specifics": specifics
        })

    @staticmethod
    def get_cpu_usage(index=2, percpu=False):
        """Get CPU usage list."""
        i = 0
        cpu_usage = None
        while i < index:
            cpu_usage = psutil.cpu_percent(interval=None, percpu=percpu)
            time.sleep(1)
            i = i + 1
        return cpu_usage

    def get_cpu_list(self, mode):
        """Returns the CPU list as per specified mode."""
        cpu_info_path = Path(self.cpu_path + mode)
        # Read the text from /cpu/online file
        cpu_info = cpu_info_path.read_text()
        # Drop the \n character from the end of string
        cpu_info = cpu_info.rstrip('\n')
        # Convert the string to list of indexes
        cpu_list = self.sysfs.convert_cpu_info_list(cpu_info)
        return cpu_list

    def get_cpu_info(self):
        """Update and return CPU information in specific format."""
        per_cpu_data = []
        cpu_present = self.get_cpu_list("present")
        cpu_online = self.get_cpu_list("online")
        cpu_usage = self.get_cpu_usage(percpu=True)
        cpu_usage_dict = dict(zip(cpu_online, cpu_usage))
        overall_cpu_usage = list(psutil.getloadavg())
        cpu_count = len(cpu_present)
        overall_usage = {
            "current": self.get_cpu_usage(percpu=False),
            "1_min_avg": overall_cpu_usage[0],
            "5_min_avg": overall_cpu_usage[1],
            "15_min_avg": overall_cpu_usage[2]
        }

        for cpu_id in range(0, cpu_count):
            uid = f"cpu_{cpu_id}"
            cpu_dict = self.get_health_template(uid, is_fru=False)
            cpu_dict["last_updated"] = int(time.time())
            online_status = "Online" if cpu_id in cpu_online else "Offline"
            health_status = "OK" if online_status == "Online" else "NA"
            usage = "NA" if health_status == "NA" \
                else cpu_usage_dict[cpu_id]
            specifics = [
                {
                    "cpu_usage": usage,
                    "state": online_status
                }
            ]
            self.set_health_data(cpu_dict, status=health_status,
                                 specifics=specifics)
            per_cpu_data.append(cpu_dict)

        cpu_data = [
            {
                "overall_usage": overall_usage,
                "cpu_count": cpu_count,
                "last_updated": int(time.time()),
                "cpus": per_cpu_data
            }
        ]
        return cpu_data

    def format_ipmi_platform_sensor_reading(self, reading):
        """builds json resposne from ipmi tool response.
        reading arg sample: ('CPU1 Temp', '01', 'ok', '3.1', '36 degrees C')
        """
        uid = '_'.join(reading[0].split())
        sensor_id = reading[0]
        sensor_props = self._ipmi.get_sensor_props(sensor_id)
        lower_critical = sensor_props[1].get('Lower Critical', 'NA')
        upper_critical = sensor_props[1].get('Upper Critical', 'NA')
        lower_non_recoverable = sensor_props[1].get('Lower Non-Recoverable', 'NA')
        upper_non_recoverable = sensor_props[1].get('Upper Non-Recoverable', 'NA')
        status = 'OK' if reading[2] == 'ok' else 'NA'
        health_desc = 'good' if status == 'OK' else 'bad'
        recommendation = sspl_constants.DEFAULT_ALERT_RECOMMENDATION if status != 'OK' else 'NA'
        resp = {
            "uid": uid,
            "fru": "false",
            "last_updated":  int(time.time()),
            "health": {
                "status": status,
                "description": f"{uid} is in {health_desc} health",
                "recommendation": f"{recommendation}",
                "specifics": [
                    {
                        "Sensor Reading": f"{reading[-1]}",
                        "lower_critical_threshold": lower_critical,
                        "upper_critical_threshold": upper_critical,
                        "lower_non_recoverable": lower_non_recoverable,
                        "upper_non_recoverable": upper_non_recoverable,
                    }
                ]
            }
        }
        return resp

    def get_platform_sensors_info(self):
        """Get the sensor information based on sensor_type and instance"""
        response = {sensor: [] for sensor in self.platform_sensor_list}
        for sensor in self.platform_sensor_list:
            sensor_reading = self._ipmi.get_sensor_list_by_type(sensor)
            for reading in sensor_reading:
                response[sensor].append(
                    self.format_ipmi_platform_sensor_reading(reading)
                )
        return response


# if __name__ == "__main__":
#     server = ServerMap()
#     health_data = server.get_health_info(
#         rpath="nodes[0]>compute[0]>hw>platform_sensors"
#     )
#     print(health_data)
