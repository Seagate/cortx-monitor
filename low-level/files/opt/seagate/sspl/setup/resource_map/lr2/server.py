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
import shlex

from socket import AF_INET
from pathlib import Path
from dbus import (SystemBus, Interface, PROPERTIES_IFACE, DBusException)
from cortx.utils.process import SimpleProcess
from resource_map import ResourceMap
from error import ResourceMapError
from cortx.utils.conf_store.error import ConfError
from framework.utils.ipmi_client import IpmiFactory
from framework.utils.tool_factory import ToolFactory
from framework.platforms.server.network import Network
from framework.utils.conf_utils import (GLOBAL_CONF, SSPL_CONF,
                                        NODE_TYPE_KEY, Conf)
from framework.base.sspl_constants import (CPU_PATH, DEFAULT_RECOMMENDATION,
                                           UNIT_IFACE, SERVICE_IFACE,
                                           MANAGER_IFACE, SYSTEMD_BUS,
                                           CORTX_RELEASE_FACTORY_INFO,
                                           CONFIG_SPEC_TYPE)


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
        self.validate_server_type_support()
        self.sysfs = ToolFactory().get_instance('sysfs')
        self.sysfs.initialize()
        self.initialize_systemd()
        self.initialize_cortx_build_info()
        self.sysfs_base_path = self.sysfs.get_sysfs_base_path()
        self.cpu_path = self.sysfs_base_path + CPU_PATH
        self.server_frus = {
            'cpu': self.get_cpu_info,
            'platform_sensors': self.get_platform_sensors_info,
            'memory': self.get_mem_info,
            'fans': self.get_fans_info,
            'nw_ports': self.get_nw_ports_info,
            'cortx_sw_services': self.get_cortx_service_info,
            'external_sw_services': self.get_external_service_info
        }
        self._ipmi = IpmiFactory().get_implementor("ipmitool")
        self.platform_sensor_list = ['Temperature', 'Voltage', 'Current']

    @staticmethod
    def validate_server_type_support():
        """Check for supported server type."""
        server_type = Conf.get(GLOBAL_CONF, NODE_TYPE_KEY).lower()
        # TODO Add support for 'virtual' type server.
        supported_types = ["physical"]
        if server_type not in supported_types:
            raise ResourceMapError(
                errno.EINVAL,
                f"Health provider is not supported for server type:{server_type}")

    def get_health_info(self, rpath):
        """
        Get health information of fru in given resource id

        rpath: Resource id (Example: nodes[0]>compute[0]>hw>disks)
        """
        info = {}
        fru_found = False
        nodes = rpath.strip().split(">")
        leaf_node, _ = self.get_node_details(nodes[-1])
        try:
            info["name"] = Conf.get("cortx_build_info", "NAME")
            info["version"] = Conf.get("cortx_build_info", "VERSION")
            info["build"] = Conf.get("cortx_build_info", "BUILD")
            info["os"] = Conf.get("cortx_build_info", "OS")
        except ConfError as e:
            # TODO add logs
            print(f"Unable to get OS & CORTX Build info: {e}")
        if leaf_node == "compute":
            for fru in self.server_frus:
                try:
                    info.update({fru: self.server_frus[fru]()})
                except:
                    # TODO: Log the exception
                    info.update({fru: None})
            info["last_updated"] = int(time.time())
            fru_found = True
        else:
            fru = None
            for node in nodes:
                fru, _ = self.get_node_details(node)
                if self.server_frus.get(fru):
                    fru_found = True
                    try:
                        info = self.server_frus[fru]()
                    except:
                        # TODO: Log the exception
                        info = None
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

    def get_fans_info(self):
        """Get the Fan sensor information using ipmitool."""
        data = []
        sensor_reading = self._ipmi.get_sensor_list_by_type('Fan')
        if sensor_reading is None:
            # TODO log error
            return
        for fan_reading in sensor_reading:
            sensor_id = fan_reading[0]
            fan_dict = self.get_health_template(sensor_id, is_fru=True)
            sensor_props = self._ipmi.get_sensor_props(sensor_id)
            status = 'OK' if fan_reading[2] == 'ok' else 'NA'
            lower_critical = sensor_props[1].get('Lower Critical', 'NA')
            upper_critical = sensor_props[1].get('Upper Critical', 'NA')
            specifics = [
                    {
                        "Sensor Reading": f"{fan_reading[-1]}",
                        "lower_critical_threshold": lower_critical,
                        "upper_critical_threshold": upper_critical
                    }
                ]

            self.set_health_data(fan_dict, status=status,
                                 specifics=specifics)

            data.append(fan_dict)
        return data

    def get_nw_ports_info(self):
        """Return the Network ports information."""
        network_cable_data = []
        io_counters = psutil.net_io_counters(pernic=True)

        nw_instance = Network()
        for interface, addrs in psutil.net_if_addrs().items():
            nic_info = self.get_health_template(interface, False)
            specifics = {}
            for addr in addrs:
                if addr.family == AF_INET:
                    specifics["ipV4"] = addr.address
            if interface in io_counters:
                io_info = io_counters[interface]
                specifics = {
                    "networkErrors": io_info.errin + io_info.errout,
                    "droppedPacketsIn": io_info.dropin,
                    "droppedPacketsOut": io_info.dropout,
                    "packetsIn": io_info.packets_recv,
                    "packetsOut": io_info.packets_sent,
                    "trafficIn": io_info.bytes_recv,
                    "trafficOut": io_info.bytes_sent
                }
            # Get the interface health status.
            nw_status, nw_cable_conn_status = \
                self.get_nw_status(nw_instance, interface)
            specifics["nwStatus"] = nw_status
            specifics["nwCableConnStatus"] = nw_cable_conn_status
            # Map and set the interface health status and description.
            map_status = {"CONNECTED": "OK", "DISCONNECTED": "Disabled/Failed",
                          "UNKNOWN": "NA"}
            health_status = map_status[nw_cable_conn_status]
            desc = "Network Interface '%s' is %sin good health." % (
                interface, '' if health_status == "OK" else 'not '
            )
            self.set_health_data(nic_info, health_status, description=desc,
                                 specifics=[specifics])
            network_cable_data.append(nic_info)
        return network_cable_data

    def get_nw_status(self, nw_interface, interface):
        """Read & Return the latest network status from sysfs files."""
        try:
            nw_status = nw_interface.get_operational_state(interface)
        except Exception:
            nw_status = "UNKNOWN"
            # Log the error when logging class is in place.
        try:
            nw_cable_conn_status = nw_interface.get_link_state(interface)
        except Exception:
            nw_cable_conn_status = "UNKNOWN"
            # Log the error when logging class is in place.
        return nw_status, nw_cable_conn_status

    def initialize_systemd(self):
        """Initialize system bus and interface."""
        self._bus = SystemBus()
        self._systemd = self._bus.get_object(
            SYSTEMD_BUS, "/org/freedesktop/systemd1")
        self._manager = Interface(self._systemd, dbus_interface=MANAGER_IFACE)

    @staticmethod
    def initialize_cortx_build_info():
        """Initialize Cortx build info."""
        if os.path.isfile(CORTX_RELEASE_FACTORY_INFO):
            cortx_build_info_file_path = "%s://%s" % (
                CONFIG_SPEC_TYPE, CORTX_RELEASE_FACTORY_INFO)
            Conf.load("cortx_build_info", cortx_build_info_file_path)

    @staticmethod
    def get_cortx_service_list():
        """Get list of cortx services for health generation."""
        # TODO use solution supplied from HA for getting
        # list of cortx services or by parsing resource xml from PCS
        cortx_services = [
            "motr-free-space-monitor.service",
            "s3authserver.service",
            "s3backgroundproducer.service",
            "s3backgroundconsumer.service",
            "hare-hax.service",
            "haproxy.service",
            "sspl-ll.service",
            "kibana.service",
            "csm_agent.service",
            "csm_web.service",
            "event_analyzer.service",
        ]
        return cortx_services

    def get_external_service_list(self):
        """Get list of external services for health generation."""
        # TODO use solution supplied from RE for getting
        # list of external services.
        external_services = set(Conf.get(
            SSPL_CONF, f"{self.SERVICE_HANDLER}>{self.SERVICE_LIST}", []))
        return external_services

    def get_cortx_service_info(self):
        """Get cortx service info in required format."""
        service_info = []
        cortx_services = self.get_cortx_service_list()
        for service in cortx_services:
            response = self.get_systemd_service_info(service)
            if response is not None:
                service_info.append(response)
        return service_info

    def get_external_service_info(self):
        """Get external service info in required format."""
        service_info = []
        external_services = self.get_external_service_list()
        for service in external_services:
            response = self.get_systemd_service_info(service)
            if response is not None:
                service_info.append(response)
        return service_info

    @staticmethod
    def get_service_info_from_rpm(service, prop):
        """
        Get specified service property from its corrosponding RPM.

        eg. (kafka.service,'LICENSE') -> 'Apache License, Version 2.0'
        """
        systemd_path_list = ["/usr/lib/systemd/system/",
                             "/etc/systemd/system/"]
        result = "NA"
        for path in systemd_path_list:
            # unit_file_path represents the path where
            # systemd service file resides
            # eg. kafka service -> /etc/systemd/system/kafka.service
            unit_file_path = path + service
            if os.path.isfile(unit_file_path):
                # this command will return the full name of RPM
                # which installs the service at given unit_file_path
                # eg. /etc/systemd/system/kafka.service -> kafka-2.13_2.7.0-el7.x86_64
                command = " ".join(["rpm", "-qf", unit_file_path])
                command = shlex.split(command)
                service_rpm, _, ret_code = SimpleProcess(command).run()
                if ret_code != 0:
                    return result
                try:
                    service_rpm = service_rpm.decode("utf-8")
                except AttributeError:
                    # TODO add logs
                    return result
                # this command will extract specified property from given RPM
                # eg. (kafka-2.13_2.7.0-el7.x86_64, 'LICENSE') -> 'Apache License, Version 2.0'
                command = " ".join(
                    ["rpm", "-q", "--queryformat", "%{"+prop+"}", service_rpm])
                command = shlex.split(command)
                result, _, ret_code = SimpleProcess(command).run()
                if ret_code != 0:
                    return result
                try:
                    # returned result should be in byte which need to be decoded
                    # eg. b'Apache License, Version 2.0' -> 'Apache License, Version 2.0'
                    result = result.decode("utf-8")
                except AttributeError:
                    # TODO add logs
                    return result
                break
        return result

    def get_systemd_service_info(self, service_name):
        """Get info of specified service using dbus API."""
        try:
            unit = self._bus.get_object(
                SYSTEMD_BUS, self._manager.LoadUnit(service_name))
            properties_iface = Interface(unit, dbus_interface=PROPERTIES_IFACE)
        except DBusException:
            # TODO add logs
            return None
        path_array = properties_iface.Get(SERVICE_IFACE, 'ExecStart')
        try:
            command_line_path = str(path_array[0][0])
        except IndexError:
            # TODO add logs
            command_line_path = "NA"

        is_installed = True if command_line_path != "NA" or 'invalid' in properties_iface.Get(
            UNIT_IFACE, 'UnitFileState') else False
        uid = str(properties_iface.Get(UNIT_IFACE, 'Id'))
        if not is_installed:
            health_status = "NA"
            health_description = f"{uid} is not installed"
            recommendation = "NA"
            specifics = [
                {
                    "service_name": uid,
                    "description": "NA",
                    "installed": str(is_installed).lower(),
                    "pid": "NA",
                    "state": "NA",
                    "substate": "NA",
                    "status": "NA",
                    "license": "NA",
                    "version": "NA",
                    "command_line_path": "NA"
                }
            ]
        else:
            service_description = str(
                properties_iface.Get(UNIT_IFACE, 'Description'))
            state = str(properties_iface.Get(UNIT_IFACE, 'ActiveState'))
            substate = str(properties_iface.Get(UNIT_IFACE, 'SubState'))
            service_status = 'enabled' if 'disabled' not in properties_iface.Get(
                UNIT_IFACE, 'UnitFileState') else 'disabled'
            pid = "NA" if state == "inactive" else str(
                properties_iface.Get(SERVICE_IFACE, 'ExecMainPID'))
            version = self.get_service_info_from_rpm(uid, "VERSION")
            service_license = self.get_service_info_from_rpm(uid, "LICENSE")
            specifics = [
                {
                    "service_name": uid,
                    "description": service_description,
                    "installed": str(is_installed).lower(),
                    "pid": pid,
                    "state": state,
                    "substate": substate,
                    "status": service_status,
                    "license": service_license,
                    "version": version,
                    "command_line_path": command_line_path
                }
            ]
            if service_status == 'enabled' and state == 'active' \
                    and substate == 'running':
                health_status = 'OK'
                health_description = f"{uid} is in good health"
                recommendation = "NA"
            else:
                health_status = substate
                health_description = f"{uid} is not in good health"
                recommendation = DEFAULT_RECOMMENDATION

        service_info = self.get_health_template(uid, is_fru=False)
        self.set_health_data(service_info, health_status,
                             health_description, recommendation, specifics)
        return service_info
