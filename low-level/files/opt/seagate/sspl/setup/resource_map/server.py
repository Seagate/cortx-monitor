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
import os
import errno
import psutil

from pathlib import Path
from dbus import (SystemBus, Interface, PROPERTIES_IFACE, DBusException)
from framework.utils.ipmi_client import IpmiFactory
from framework.utils.tool_factory import ToolFactory
from cortx.utils.process import SimpleProcess
from resource_map import ResourceMap
from error import ResourceMapError
from framework.utils.conf_utils import (SSPL_CONF, Conf)
from framework.base.sspl_constants import (CPU_PATH, UNIT_IFACE, SERVICE_IFACE,
        MANAGER_IFACE, SYSTEMD_BUS, DEFAULT_RECOMMENDATION,
        CORTX_RELEASE_FACTORY_INFO)


class ServerMap(ResourceMap):
    """ServerMap class provides resource map and related information
    like health, manifest, etc,.
    """

    name = "server"

    SERVICE_HANDLER = 'SERVICEMONITOR'
    SERVICE_LIST = 'monitored_services'

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
            'memory': self.get_mem_info,
            'cortx_sw_services': self.get_cortx_service_info,
            'external_sw_services': self.get_external_service_info
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
            uid = f"CPU-{cpu_id}"
            cpu_dict = self.get_health_template(uid, is_fru=False)
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
        description = f"{uid} sensor is in {health_desc} health."
        recommendation = DEFAULT_RECOMMENDATION if status != 'OK' else 'NA'
        specifics = [
            {
                "Sensor Reading": f"{reading[-1]}",
                "lower_critical_threshold": lower_critical,
                "upper_critical_threshold": upper_critical,
                "lower_non_recoverable": lower_non_recoverable,
                "upper_non_recoverable": upper_non_recoverable,
                }
            ]
        resp = self.get_health_template(uid, is_fru=False)
        self.set_health_data(
            resp, status, description, recommendation, specifics)
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

    def get_mem_info(self):
        """Collect & return system memory info in specific format """
        from framework.utils.conf_utils import SSPL_CONF, Conf
        default_mem_usage_threshold = int(Conf.get(SSPL_CONF,
            "NODEDATAMSGHANDLER>host_memory_usage_threshold",
            80))
        data = []
        status = "OK"
        description = "Host memory is in good health."
        self.mem_info = dict(psutil.virtual_memory()._asdict())
        curr_mem_usage_threshold = int(self.mem_info['percent'])
        if curr_mem_usage_threshold > int(default_mem_usage_threshold):
            status = "Overloaded"
            description = (f"Current host memory usage is {curr_mem_usage_threshold},"
                           f"beyond configured threshold of {default_mem_usage_threshold}.")

        memory_dict = self.prepare_mem_json(status,
                                            description)
        data.append(memory_dict)
        return data

    def prepare_mem_json(self, status, description):
        """Update and return memory information dict """
        total_memory = {}
        for key, value in self.mem_info.items():
            if key == 'percent':
                total_memory['percent'] = str(self.mem_info['percent']) + '%'
            else:
                total_memory[key] = str(self.mem_info[key] >> 20) + 'MB'
        uid = "main_memory"
        specifics = [
                    {
                        "total": total_memory['total'],
                        "available": total_memory['available'],
                        "percent": total_memory['percent'],
                        "used": total_memory['used'],
                        "free": total_memory['free'],
                        "active": total_memory['active'],
                        "inactive": total_memory['inactive'],
                        "buffers": total_memory['buffers'],
                        "cached": total_memory['cached'],
                        "shared": total_memory['shared'],
                        "slab": total_memory['slab']
                    }
                ]
        memory_dict = self.get_health_template(uid, is_fru=False)
        self.set_health_data(
            memory_dict, status=status, description=description,
            specifics=specifics)
        return memory_dict

    def initialize_systemd(self):
        """Initialize system bus and interface."""
        self._bus = SystemBus()
        self._systemd = self._bus.get_object(
            SYSTEMD_BUS, "/org/freedesktop/systemd1")
        self._manager = Interface(self._systemd, dbus_interface=MANAGER_IFACE)

    def get_cortx_build_info(self):
        """Get Cortx build info."""
        cortx_build_info = None
        if os.path.isfile(CORTX_RELEASE_FACTORY_INFO):
            Conf.load(cortx_build_info, CORTX_RELEASE_FACTORY_INFO)
        return cortx_build_info

    def get_cortx_service_info(self):
        """Get cortx service info in required format."""
        service_info = []
        # TODO Get list of services from HA
        return service_info

    def get_external_service_info(self):
        """Get external service info in required format."""
        service_info = []
        external_services = set(Conf.get(
            SSPL_CONF, f"{self.SERVICE_HANDLER}>{self.SERVICE_LIST}", []))
        for service in external_services:
            response = self.get_systemd_service_info(service)
            service_info.append(response)
        return service_info

    def get_service_info_from_rpm(self, service, prop):
        """Get service info from its corrosponding RPM."""
        systemd_path_list = ["/usr/lib/systemd/system/",
                    "/etc/systemd/system/"]
        result = None
        for path in systemd_path_list:
            unit_file_path = path + service
            if os.path.isfile(unit_file_path):
                service_rpm, _, _ = SimpleProcess.run(
                    ["rpm", "-qf", unit_file_path])
                result, _, _ = SimpleProcess.run(
                    ["rpm", "-q", "--queryformat", "%{"+prop+"}", service_rpm])
                break
        return result

    def get_systemd_service_info(self, service_name):
        """Get info of specified service using dbus API."""
        self.initialize_systemd()
        try:
            unit = self._bus.get_object(
                SYSTEMD_BUS, self._manager.LoadUnit(service_name))
            properties_iface = Interface(unit, dbus_interface=PROPERTIES_IFACE)
        except DBusException:
            # TODO add logs
            return
        path_array = properties_iface.Get(SERVICE_IFACE, 'ExecStart')
        try:
            command_line_path = str(path_array[0][0])
        except IndexError:
            # TODO add logs
            command_line_path = None
        if command_line_path is None or \
                'invalid' in properties_iface.Get(UNIT_IFACE, 'UnitFileState'):
            return

        is_installed = True if command_line_path is not None else False
        uid = str(properties_iface.Get(UNIT_IFACE, 'Id'))
        pid = str(properties_iface.Get(SERVICE_IFACE, 'ExecMainPID'))
        description = str(properties_iface.Get(UNIT_IFACE, 'Description'))
        state = str(properties_iface.Get(UNIT_IFACE, 'ActiveState'))
        substate = str(properties_iface.Get(UNIT_IFACE, 'SubState'))
        version = self.get_service_info_from_rpm(uid, "VERSION")
        license = self.get_service_info_from_rpm(uid, "LICENSE")
        specific_status = 'enabled' if 'disabled' not in properties_iface.Get(
            UNIT_IFACE, 'UnitFileState') else 'disabled'
        if specific_status == 'enabled' and state == 'active' \
                and substate == 'running':
            status = 'OK'
        else:
            status = substate
        specifics = [
            {
                "service_name": uid,
                "description": description,
                "installed": is_installed,
                "pid": pid,
                "state": state,
                "substate": substate,
                "status": specific_status,
                "license": license,
                "version": version,
                "command_line_path": command_line_path
            }
        ]
        service_info = self.get_health_template(uid, is_fru=False)
        self.set_health_data(
            service_info, status, specifics=specifics)
        return service_info
