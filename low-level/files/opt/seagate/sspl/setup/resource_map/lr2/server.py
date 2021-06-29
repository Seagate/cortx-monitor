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
import errno
import psutil
import socket
from pathlib import Path
from dbus import (Interface, PROPERTIES_IFACE, DBusException)

from error import ResourceMapError
from resource_map import ResourceMap
from framework.base.sspl_constants import (
    CPU_PATH, DEFAULT_RECOMMENDATION, UNIT_IFACE, SERVICE_IFACE,
    SYSTEMD_BUS, SAS_RESOURCE_ID, HEALTH_SVC_NAME)
from framework.platforms.server.raid.raid import RAIDs
from framework.platforms.server.software import BuildInfo, Service
from framework.platforms.server.network import Network
from framework.platforms.server.sas import SAS
from framework.platforms.server.error import (
    SASError, NetworkError, BuildInfoError, ServiceError)
from framework.platforms.server.platform import Platform
from framework.platforms.server.sas import SAS
from framework.platforms.server.error import SASError, NetworkError
from framework.utils.conf_utils import (
    Conf, GLOBAL_CONF, SSPL_CONF, NODE_TYPE_KEY)
from framework.utils.service_logging import CustomLog, logger
from framework.utils.ipmi_client import IpmiFactory
from framework.utils.tool_factory import ToolFactory

class ServerMap(ResourceMap):
    """ServerMap class provides resource map and related information
    like health, manifest, etc,.
    """

    name = "server"

    def __init__(self):
        """Initialize server"""
        super().__init__()
        self.log = CustomLog(HEALTH_SVC_NAME)
        self.validate_server_type_support()
        self.sysfs = ToolFactory().get_instance('sysfs')
        self.sysfs.initialize()
        self.sysfs_base_path = self.sysfs.get_sysfs_base_path()
        self.cpu_path = self.sysfs_base_path + CPU_PATH
        hw_resources = {
            'cpu': self.get_cpu_info,
            'platform_sensors': self.get_platform_sensors_info,
            'memory': self.get_mem_info,
            'fans': self.get_fans_info,
            'nw_ports': self.get_nw_ports_info,
            'cortx_sw_services': self.get_cortx_service_info,
            'external_sw_services': self.get_external_service_info,
            'sas_hba': self.get_sas_hba_info,
            'sas_ports': self.get_sas_ports_info,
            'nw_ports': self.get_nw_ports_info,
            'raid': self.get_raid_info
        }
        sw_resources = {}
        self.server_resources = {
            "hw": hw_resources,
            "sw": sw_resources
        }
        self._ipmi = IpmiFactory().get_implementor("ipmitool")
        self.platform_sensor_list = ['Temperature', 'Voltage', 'Current']

    def validate_server_type_support(self):
        """Check for supported server type."""
        server_type = Conf.get(GLOBAL_CONF, NODE_TYPE_KEY).lower()
        # TODO Add support for 'virtual' type server.
        logger.debug(self.log.svc_log(f"Server Type:{server_type}"))
        supported_types = ["physical"]
        if server_type not in supported_types:
            msg = f"Health provider is not supported for server type:{server_type}"
            logger.error(self.log.svc_log(msg))
            raise ResourceMapError(errno.EINVAL, msg)

    def get_health_info(self, rpath):
        """
        Fetch health information for given rpath

        rpath: Resource path to fetch its health
               Examples:
                    node>compute[0]
                    node>compute[0]>hw
                    node>compute[0]>hw>disks
        """
        logger.info(self.log.svc_log(
            f"Get Health data for rpath:{rpath}"))
        info = {}
        resource_found = False
        nodes = rpath.strip().split(">")
        leaf_node, _ = self.get_node_details(nodes[-1])
        build_instance = BuildInfo()
        try:
            info["name"] = build_instance.get_attribute("NAME")
            info["version"] = build_instance.get_attribute("VERSION")
            info["build"] = build_instance.get_attribute("BUILD")
        except BuildInfoError as err:
            logger.error(self.log.svc_log(
                f"Unable to get build info due to {err}"))

        # Fetch health information for all sub nodes
        if leaf_node == "compute":
            info = self.get_server_health_info()
            resource_found = True
        elif leaf_node in self.server_resources:
            for resource, method in self.server_resources[leaf_node].items():
                try:
                    info.update({resource: method()})
                    resource_found = True
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}:{err}"))
                    info = None
        else:
            for node in nodes:
                resource, _ = self.get_node_details(node)
                for res_type in self.server_resources:
                    method = self.server_resources[res_type].get(resource)
                    if not method:
                        continue
                    try:
                        info = method()
                        resource_found = True
                    except Exception as err:
                        logger.error(
                            self.log.svc_log(f"{err.__class__.__name__}:{err}"))
                        info = None
                if resource_found:
                    break

        if not resource_found:
            msg = f"Invalid rpath or health provider doesn't have support for'{rpath}'."
            logger.error(self.log.svc_log(f"{msg}"))
            raise ResourceMapError(errno.EINVAL, msg)

        return info

    def _is_any_resource_unhealthy(self, fru, data):
        """Check for any unhealthy resource at child level"""
        for child in data[fru]:
            if isinstance(child, dict):
                if child.get("health") and \
                    child["health"]["status"].lower() != "ok":
                    return True
        return False

    def get_server_health_info(self):
        """Returns overall server information"""
        unhealthy_resource_found = False
        server_details = Platform().get_server_details()
        # Currently only one instance of server is considered
        server = []
        info = {}
        info["make"] = server_details["Board Mfg"]
        info["model"]= server_details["Product Name"]
        info["resource_usage"] = {}
        info["resource_usage"]["cpu_usage"] = self.get_cpu_overall_usage()
        info["resource_usage"]["disk_usage"] = self.get_disk_overall_usage()
        info["resource_usage"]["memory_usage"] = self.get_memory_overall_usage()

        for res_type in self.server_resources:
            info.update({res_type: {}})
            for fru, method in self.server_resources[res_type].items():
                try:
                    info[res_type].update({fru: method()})
                    unhealthy_resource_found = self._is_any_resource_unhealthy(
                        fru, info[res_type])
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}:{err}"))
                    info[res_type].update({fru: None})

        info["uid"] = socket.getfqdn()
        info["last_updated"] = int(time.time())
        info["health"] = {}
        info["health"]["status"] = "OK" if not unhealthy_resource_found else "Degraded"
        health_desc = 'good' if info["health"]["status"] == 'OK' else 'bad'
        info["health"]["description"] = f"Server is in {health_desc} health."
        info["health"]["recommendation"] = DEFAULT_RECOMMENDATION \
            if info["health"]["status"] != "OK" else "NA"
        info["health"]["specifics"] = []
        server.append(info)
        return server

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

    def get_cpu_info(self, add_overall_usage=False):
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
        if not add_overall_usage:
            cpu_data = per_cpu_data

        logger.debug(self.log.svc_log(
            f"CPU Health Data:{cpu_data}"))
        return cpu_data

    def get_cpu_overall_usage(self):
        """Returns CPU overall usage"""
        overall_usage = None
        cpu_data = self.get_cpu_info(add_overall_usage=True)
        if cpu_data[0].get("overall_usage"):
            overall_usage = cpu_data[0].get("overall_usage")
        else:
            logger.error(
                self.log.svc_log("Failed to get overall cpu usage"))
        return overall_usage

    def get_disk_info(self, add_overall_usage=False):
        """Update and return Disk information in specific format."""
        per_disk_data = []
        overall_usage = None
        disk_data = [
            {
                "overall_usage": overall_usage,
                "last_updated": int(time.time()),
                "disks": per_disk_data
            }
        ]
        if not add_overall_usage:
            disk_data = per_disk_data

        logger.debug(self.log.svc_log(
            f"Disk Health Data:{disk_data}"))
        return disk_data

    def get_disk_overall_usage(self):
        """Returns Disk overall usage"""
        overall_usage = None
        disk_data = self.get_disk_info(add_overall_usage=True)
        if disk_data[0].get("overall_usage"):
            overall_usage = disk_data[0].get("overall_usage")
        else:
            logger.error(
                self.log.svc_log("Failed to get overall disk usage"))
        return overall_usage

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
            if not sensor_reading:
                logger.debug(self.log.svc_log(f"No sensor data received for :{sensor}"))
                continue
            for reading in sensor_reading:
                response[sensor].append(
                    self.format_ipmi_platform_sensor_reading(reading)
                )
        logger.debug(self.log.svc_log(
            f"Platform Sensor Health Data:{response}"))
        return response

    def get_mem_info(self):
        """Collect & return system memory info in specific format """
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
        logger.debug(self.log.svc_log(
            f"Memory Health Data:{data}"))
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

    def get_memory_overall_usage(self):
        """Returns Memory overall usage"""
        overall_usage = None
        mem_info = self.get_mem_info()
        if mem_info[0].get("health"):
            overall_usage = mem_info[0]["health"]["specifics"]
        else:
            logger.error(
                self.log.svc_log("Failed to get memory overall usage"))
        return overall_usage

    def get_fans_info(self):
        """Get the Fan sensor information using ipmitool."""
        data = []
        sensor_reading = self._ipmi.get_sensor_list_by_type('Fan')
        if sensor_reading is None:
            msg = f"Failed to get Fan sensor reading using ipmitool"
            logger.error(self.log.svc_log(msg))
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
            logger.debug(self.log.svc_log(
                f"Fan Health Data:{fan_dict}"))
        return data

    def get_sas_hba_info(self):
        """Return SAS-HBA current health."""
        sas_hba_data = []
        sas_instance = SAS()
        try:
            hosts = sas_instance.get_host_list()  # ['host1']
        except SASError as err:
            hosts = []
            logger.error(self.log.svc_log(err))
        except Exception as err:
            hosts = []
            logger.exception(self.log.svc_log(err))

        for host in hosts:
            host_id = SAS_RESOURCE_ID + host.replace('host', '')
            host_data = self.get_health_template(host_id, False)
            try:
                ports = sas_instance.get_port_list(host)
                # ports = ['port-1:0', 'port-1:1', 'port-1:2', 'port-1:3']
            except SASError as err:
                ports = []
                logger.error(self.log.svc_log(err))
            except Exception as err:
                ports = []
                logger.exception(self.log.svc_log(err))
            health = "OK"
            specifics = {
                'num_ports': len(ports),
                'ports': []
            }
            for port in ports:
                try:
                    port_data = sas_instance.get_port_data(port)
                except SASError as err:
                    port_data = []
                    logger.error(self.log.svc_log(err))
                except Exception as err:
                    port_data = []
                    logger.exception(self.log.svc_log(err))
                specifics['ports'].append(port_data)
                if not port_data or port_data['state'] != 'running':
                    health = "NA"
            self.set_health_data(host_data, health, specifics=[specifics])
            sas_hba_data.append(host_data)
        return sas_hba_data

    def get_sas_ports_info(self):
        """Return SAS Ports current health."""
        sas_ports_data = []
        sas_instance = SAS()
        try:
            ports = sas_instance.get_port_list()
            # eg: ['port-1:0', 'port-1:1', 'port-1:2', 'port-1:3']
        except SASError as err:
            ports = []
            logger.error(self.log.svc_log(err))
        except Exception as err:
            ports = []
            logger.exception(self.log.svc_log(err))

        for port in ports:
            port_id = 'sas_' + port
            port_data = self.get_health_template(port_id, False)
            try:
                phys = sas_instance.get_phy_list_for_port(port)
                # eg: [ 'phy-1:0', 'phy-1:1', 'phy-1:2', 'phy-1:3']
            except SASError as err:
                phys = []
                logger.error(self.log.svc_log(err))
            except Exception as err:
                phys = []
                logger.exception(self.log.svc_log(err))
            specifics = {
                'num_phys': len(phys),
                'phys': []
            }
            health = "OK"
            for phy in phys:
                try:
                    phy_data = sas_instance.get_phy_data(phy)
                except SASError as err:
                    phy_data = {}
                    logger.error(self.log.svc_log(err))
                except Exception:
                    phy_data = {}
                    logger.exception(self.log.svc_log(err))
                specifics['phys'].append(phy_data)
                if not phy_data or phy_data['state'] != 'enabled' or \
                   'Gbit' not in phy_data['negotiated_linkrate']:
                    health = "NA"
            self.set_health_data(port_data, health, specifics=[specifics])
            sas_ports_data.append(port_data)
        return sas_ports_data

    def get_nw_ports_info(self):
        """Return the Network ports information."""
        network_cable_data = []
        io_counters = psutil.net_io_counters(pernic=True)

        nw_instance = Network()
        for interface, addrs in psutil.net_if_addrs().items():
            nic_info = self.get_health_template(interface, False)
            specifics = {}
            for addr in addrs:
                if addr.family == socket.AF_INET:
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
        except NetworkError as err:
            nw_status = "UNKNOWN"
            logger.error(self.log.svc_log(err))
        except Exception as err:
            nw_status = "UNKNOWN"
            logger.exception(self.log.svc_log(err))
        try:
            nw_cable_conn_status = nw_interface.get_link_state(interface)
        except NetworkError as err:
            nw_cable_conn_status = "UNKNOWN"
            logger.exception(self.log.svc_log(err))
        except Exception as err:
            nw_cable_conn_status = "UNKNOWN"
            logger.exception(self.log.svc_log(err))
        return nw_status, nw_cable_conn_status

    def get_cortx_service_info(self):
        """Get cortx service info in required format."""
        service_info = []
        cortx_services = Service().get_cortx_service_list()
        for service in cortx_services:
            response = self.get_systemd_service_info(service)
            if response is not None:
                service_info.append(response)
        return service_info

    def get_external_service_info(self):
        """Get external service info in required format."""
        service_info = []
        external_services = Service().get_external_service_list()
        for service in external_services:
            response = self.get_systemd_service_info(service)
            if response is not None:
                service_info.append(response)
        return service_info

    def get_systemd_service_info(self, service_name):
        """Get info of specified service using dbus API."""
        try:
            unit = Service()._bus.get_object(
                SYSTEMD_BUS, Service()._manager.LoadUnit(service_name))
            properties_iface = Interface(unit, dbus_interface=PROPERTIES_IFACE)
        except DBusException as err:
            logger.error(self.log.svc_log(
                f"Unable to initialize {service_name} due to {err}"))
            return None
        path_array = properties_iface.Get(SERVICE_IFACE, 'ExecStart')
        try:
            command_line_path = str(path_array[0][0])
        except IndexError as err:
            logger.error(self.log.svc_log(
                f"Unable to find {service_name} path due to {err}"))
            command_line_path = "NA"

        is_installed = True if command_line_path != "NA" or 'invalid' in properties_iface.Get(
            UNIT_IFACE, 'UnitFileState') else False
        uid = str(properties_iface.Get(UNIT_IFACE, 'Id'))
        if not is_installed:
            health_status = "NA"
            health_description = f"Software enabling {uid} is not installed"
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
            service_license = "NA"
            version = "NA"
            service_description = str(
                properties_iface.Get(UNIT_IFACE, 'Description'))
            state = str(properties_iface.Get(UNIT_IFACE, 'ActiveState'))
            substate = str(properties_iface.Get(UNIT_IFACE, 'SubState'))
            service_status = 'enabled' if 'disabled' not in properties_iface.Get(
                UNIT_IFACE, 'UnitFileState') else 'disabled'
            pid = "NA" if state == "inactive" else str(
                properties_iface.Get(SERVICE_IFACE, 'ExecMainPID'))
            try:
                version = Service().get_service_info_from_rpm(
                    uid, "VERSION")
            except ServiceError as err:
                logger.error(self.log.svc_log(
                    f"Unable to get service version due to {err}"))
            try:
                service_license = Service().get_service_info_from_rpm(
                    uid, "LICENSE")
            except ServiceError as err:
                logger.error(self.log.svc_log(
                    f"Unable to get service license due to {err}"))

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
                health_status = state
                health_description = f"{uid} is not in good health"
                recommendation = DEFAULT_RECOMMENDATION

        service_info = self.get_health_template(uid, is_fru=False)
        self.set_health_data(service_info, health_status,
                             health_description, recommendation, specifics)
        return service_info

    def get_raid_info(self):
        raids_data = []
        for raid in RAIDs.get_configured_raids():
            raid_data = self.get_health_template(raid.id, False)
            health, description = raid.get_health()
            devices = raid.get_devices()
            specifics = [{"location": raid.raid,
                          "data_integrity_status": raid.get_data_integrity_status(),
                          "devices": devices}]
            self.set_health_data(raid_data, health, specifics=specifics, description=description)
            raids_data.append(raid_data)
        return raids_data
