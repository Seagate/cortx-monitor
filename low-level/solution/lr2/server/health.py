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

import errno
import re
import socket
import time
from pathlib import Path

import psutil
from cortx.utils.process import SimpleProcess
from cortx.utils.discovery.error import ResourceMapError
from framework.base import sspl_constants as const
from framework.platforms.server.disk import Disk
from framework.platforms.server.error import NetworkError, SASError
from framework.platforms.server.network import Network
from framework.platforms.server.platform import Platform
from framework.platforms.server.raid import RAIDs
from framework.platforms.server.sas import SAS
from framework.platforms.server.software import BuildInfo, Service
from framework.utils.mon_utils import MonUtils
from framework.utils.conf_utils import (GLOBAL_CONF, NODE_TYPE_KEY, SSPL_CONF,
                                        Conf)
from framework.utils.ipmi_client import IpmiFactory
from framework.utils.service_logging import CustomLog, logger
from framework.utils.tool_factory import ToolFactory
from server.server_resource_map import ServerResourceMap


class ServerHealth():
    """
    ServerHealth class provides resource map and related information
    like health.
    """

    name = "server_health"

    def __init__(self):
        """Initialize server."""
        super().__init__()
        self.log = CustomLog(const.HEALTH_SVC_NAME)
        server_type = Conf.get(GLOBAL_CONF, NODE_TYPE_KEY)
        Platform.validate_server_type_support(self.log, ResourceMapError, server_type)
        self.sysfs = ToolFactory().get_instance('sysfs')
        self.sysfs.initialize()
        self.sysfs_base_path = self.sysfs.get_sysfs_base_path()
        self.cpu_path = self.sysfs_base_path + const.CPU_PATH
        hw_resources = {
            'cpu': self.get_cpu_info,
            'platform_sensor': self.get_platform_sensors_info,
            'memory': self.get_mem_info,
            'fan': self.get_fans_info,
            'nw_port': self.get_nw_ports_info,
            'sas_hba': self.get_sas_hba_info,
            'sas_port': self.get_sas_ports_info,
            'disk': self.get_disks_info,
            'psu': self.get_psu_info
        }
        sw_resources = {
            'cortx_sw_services': self.get_cortx_service_info,
            'external_sw_services': self.get_external_service_info,
            'raid': self.get_raid_info
        }
        self.server_resources = {
            "hw": hw_resources,
            "sw": sw_resources
        }
        self._ipmi = IpmiFactory().get_implementor("ipmitool")
        self.platform_sensor_list = ['Temperature', 'Voltage', 'Current']
        self.service = Service()
        self.resource_indexing_map = ServerResourceMap.resource_indexing_map\
            ["health"]

    def get_data(self, rpath):
        """Fetch health information for given rpath."""
        logger.info(self.log.svc_log(
            f"Get Health data for rpath:{rpath}"))
        info = {}
        resource_found = False
        nodes = rpath.strip().split(">")
        leaf_node, _ = ServerResourceMap.get_node_info(nodes[-1])

        # Fetch health information for all sub nodes
        if leaf_node == "server":
            info = self.get_server_health_info()
            resource_found = True
        elif leaf_node in self.server_resources:
            for resource, method in self.server_resources[leaf_node].items():
                try:
                    info.update({resource: method()})
                    resource_found = True
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}: {err}"))
                    info = None
        else:
            for node in nodes:
                resource, _ = ServerResourceMap.get_node_info(node)
                for res_type in self.server_resources:
                    method = self.server_resources[res_type].get(resource)
                    if not method:
                        logger.error(
                            self.log.svc_log(
                                f"No mapping function found for {res_type}"))
                        continue
                    try:
                        info = method()
                        resource_found = True
                    except Exception as err:
                        logger.error(
                            self.log.svc_log(f"{err.__class__.__name__}: {err}"))
                        info = None
                if resource_found:
                    break

        if not resource_found:
            msg = f"Invalid rpath or health provider doesn't have support for'{rpath}'."
            logger.error(self.log.svc_log(f"{msg}"))
            raise ResourceMapError(errno.EINVAL, msg)

        info = MonUtils.normalize_kv(info, const.HEALTH_UNDESIRED_VALS,
            "Not Available")
        return info

    @staticmethod
    def _is_any_resource_unhealthy(fru, data):
        """Check for any unhealthy resource at child level."""
        for child in data[fru]:
            if isinstance(child, dict):
                if child.get("health") and \
                    child["health"]["status"].lower() != "ok":
                    return True
        return False

    @staticmethod
    def get_health_template(uid, is_fru: bool):
        """Returns health template."""
        return {
            "uid": uid,
            "fru": str(is_fru).lower(),
            "last_updated": "",
            "health": {
                "status": "",
                "description": "",
                "recommendation": "",
                "specifics": []
            }
        }

    @staticmethod
    def set_health_data(health_data: dict, status, description=None,
                        recommendation=None, specifics=None):
        """Sets health attributes for a component."""
        good_state = (status == "OK")
        if not description or \
            description in const.HEALTH_UNDESIRED_VALS:
            description = "%s %s in good health." % (
                health_data.get("uid"),
                'is' if good_state else 'is not')
        if not good_state:
            if not recommendation or \
                recommendation in const.HEALTH_UNDESIRED_VALS:
                    recommendation = const.DEFAULT_RECOMMENDATION
        else:
            recommendation = "None"
        health_data["last_updated"] = int(time.time())
        health_data["health"].update({
            "status": status,
            "description": description,
            "recommendation": recommendation,
            "specifics": specifics
        })

    def get_server_health_info(self):
        """Returns overall server information."""
        unhealthy_resource_found = False
        server_details = Platform().get_server_details()
        # Currently only one instance of server is considered
        server = []
        info = {}
        info["make"] = server_details["Board Mfg"]
        info["model"]= server_details["Product Name"]
        try:
            build_instance = BuildInfo()
            info["product_family"] = build_instance.get_attribute("NAME")
            info["version"] = build_instance.get_attribute("VERSION")
            info["build"] = build_instance.get_attribute("BUILD")
        except Exception as err:
            logger.error(self.log.svc_log(
                f"Unable to get build info due to {err}"))
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
        info["health"]["recommendation"] = const.DEFAULT_RECOMMENDATION \
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

        sort_key_path = self.resource_indexing_map["hw"]["cpu"]
        cpu_data = MonUtils.sort_by_specific_kv(cpu_data, sort_key_path, self.log)
        logger.debug(self.log.svc_log(
            f"CPU Health Data:{cpu_data}"))
        return cpu_data

    def get_cpu_overall_usage(self):
        """Returns CPU overall usage."""
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

    def format_ipmi_platform_sensor_reading(self, reading):
        """
        builds json response from ipmi tool response.
        reading arg sample: ('CPU1 Temp', '01', 'ok', '3.1', '36 degrees C').
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
        recommendation = const.DEFAULT_RECOMMENDATION if status != 'OK' else 'NA'
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
        """Get the sensor information based on sensor_type and instance."""
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
        """Collect & return system memory info in specific format."""
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
        """Update and return memory information dict."""
        total_memory = {}
        for key, value in self.mem_info.items():
            if key == 'percent':
                total_memory[key] = str(value) + '%'
            else:
                total_memory[key] = str(value >> 20) + 'MB'
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
        """Returns Memory overall usage."""
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
            msg = "Failed to get Fan sensor reading using ipmitool"
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
            host_id = const.SAS_RESOURCE_ID + host.replace('host', '')
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
                except Exception as err:
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
        loopback_interface = {}
        sort_key_path = None
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
            specifics["logical_name"] = interface
            # Map and set the interface health status and description.
            map_status = {"CONNECTED": "OK", "DISCONNECTED": "Disabled/Failed",
                          "UNKNOWN": "NA"}
            health_status = map_status[nw_cable_conn_status]
            desc = "Network Interface '%s' is %sin good health." % (
                interface, '' if health_status == "OK" else 'not '
            )
            self.set_health_data(nic_info, health_status, description=desc,
                                 specifics=[specifics])
            # Separating out loopback interface and ethernet interface
            # data to make correct sorting/mapping with manifest data.
            if interface == 'lo':
                loopback_interface = nic_info
            else:
                network_cable_data.append(nic_info)
        sort_key_path = self.resource_indexing_map["hw"]["nw_port"]
        network_cable_data = MonUtils.sort_by_specific_kv(
            network_cable_data, sort_key_path, self.log)
        if loopback_interface:
            network_cable_data.append(loopback_interface)
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
        cortx_services = self.service.get_cortx_service_list()
        cortx_service_info = self.get_service_info(cortx_services)
        sort_key_path = self.resource_indexing_map["sw"]["cortx_sw_services"]
        cortx_service_info = MonUtils.sort_by_specific_kv(
            cortx_service_info, sort_key_path, self.log)
        return cortx_service_info

    def get_external_service_info(self):
        """Get external service info in required format."""
        external_services = self.service.get_external_service_list()
        external_service_info = self.get_service_info(external_services)
        sort_key_path = self.resource_indexing_map["sw"]["external_sw_services"]
        external_service_info = MonUtils.sort_by_specific_kv(
            external_service_info, sort_key_path, self.log)
        return external_service_info

    def get_service_info(self, services):
        services_info = []
        for service in services:
            response = self.service.get_systemd_service_info(self.log, service)
            if response is not None:
                uid, health_status, health_description, recommendation, \
                    specifics = response
                service_info = self.get_health_template(uid, is_fru=False)
                self.set_health_data(service_info, health_status,
                    health_description, recommendation, specifics)
                services_info.append(service_info)
        return services_info

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

    @staticmethod
    def get_disk_overall_usage():
        units_factor_GB = 1000000000
        overall_usage = {
                "totalSpace": f'{int(psutil.disk_usage("/")[0])//int(units_factor_GB)} GB',
                "usedSpace": f'{int(psutil.disk_usage("/")[1])//int(units_factor_GB)} GB',
                "freeSpace": f'{int(psutil.disk_usage("/")[2])//int(units_factor_GB)} GB',
                "diskUsedPercentage": psutil.disk_usage("/")[3],
            }
        return overall_usage

    def get_disks_info(self):
        """Update and return server drive information in specific format."""
        disks = []
        sort_key_path = None
        for disk in Disk.get_disks():
            uid = disk.path if disk.path else disk.id
            disk_health = self.get_health_template(uid, True)
            health_data = disk.get_health()
            health = "OK" if (health_data['SMART_health'] == "PASSED") else "Fault"
            serial_number = disk.id.split("-")[-1] if disk.id else "NA"
            health_data.update({"serial_number": serial_number})
            self.set_health_data(disk_health, health, specifics=[{
                "SMART": health_data}])
            disks.append(disk_health)
        # Sort disk list by serial_number
        sort_key_path = self.resource_indexing_map["hw"]["disk"]
        disks = MonUtils.sort_by_specific_kv(disks, sort_key_path,
            self.log)
        logger.debug(self.log.svc_log(
            f"Disk Health Data:{disks}"))
        return disks

    def get_psu_info(self):
        """Update and return PSU information in specific format."""
        psus_data = []
        sort_key_path = None
        for psu in self.get_psus():
            psu = {k.lower().replace(" ", "_"): v for k,v in psu.items()}
            data = self.get_health_template(f'{psu["location"]}', True)
            health = "OK" if (psu["status"] == "Present, OK") else "Fault"
            self.set_health_data(data, health, specifics=psu)
            psus_data.append(data)
        # Sort disk list by serial_number
        sort_key_path = self.resource_indexing_map["hw"]["psu"]
        psus_data = MonUtils.sort_by_specific_kv(psus_data,
            sort_key_path, self.log)
        logger.debug(self.log.svc_log(
            f"PSU Health Data:{psus_data}"))
        return psus_data

    @staticmethod
    def get_psus():
        response, _, _ = SimpleProcess("dmidecode -t 39").run()
        matches = re.findall("System Power Supply|Power Unit Group:.*|"
                             "Location:.*|Name:.*|Serial Number:.*|"
                             "Max Power Capacity:.*|Status: .*|"
                             "Plugged:.*|Hot Replaceable:.*", response.decode())
        psus = []
        stack = []
        while matches:
            item = matches.pop()
            while item != "System Power Supply":
                stack.append(item)
                item = matches.pop()
            psu = {}
            while stack:
                key, value = stack.pop().strip().split(":")
                psu[key] = value.strip()
            psus.append(psu)
        return psus
