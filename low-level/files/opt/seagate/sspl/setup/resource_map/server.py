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
import os
import re
import psutil
import socket
from resource_map import ResourceMap
from error import ResourceMapError

from framework.utils.tool_factory import ToolFactory


class ServerMap(ResourceMap):
    """Provides server resource related information."""

    name = "server"
    SAS_RESOURCE_ID = ["SASHBA-0"]
    NW_CBL_CARRIER_FILE = "/sys/class/net/%s/carrier"
    NW_CBL_OPERSTATE_FILE = "/sys/class/net/%s/operstate"

    def __init__(self):
        """Initialize server."""
        super().__init__()
        self.server_frus = {
            'sas_hba': self.get_sas_hba_info,
            'sas_ports': self.get_sas_ports_info,
            'nw_ports': self.get_nw_ports_info
        }
        self.sysfs = ToolFactory().get_instance('sysfs')
        self.sysfs.initialize()

    def get_health_info(self, rpath):
        """
        Get health information of fru in given resource id.

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

    def get_data_template(self, uid, is_fru: bool):
        """Get the health data template."""
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

    def set_health_data(self, obj: dict, status, description=None,
                        recommendation=None):
        """Set the given or default health data as per health status."""
        good_state = (status == "OK")
        if not description:
            description = "%s is %sin good state" % (
                            obj.get("uid"),
                            '' if good_state else 'not ')
        if not recommendation:
            recommendation = 'None' if good_state\
                             else "Contact Seagate Support."

        obj["health"].update({
            "status": status,
            "description": description,
            "recommendation": recommendation
        })

    def get_sas_hba_info(self):
        """Return the s SAS-HBA information."""
        return self.get_sas_ports_info("sas_hba")

    def get_sas_ports_info(self, leaf_node="sas_ports"):
        """Return the s SAS ports information."""
        sas_hba_data = []
        health_data = []
        for sas_rid in self.SAS_RESOURCE_ID:
            r_data = self.get_data_template(sas_rid, False)
            sas_ports_dict = self.sysfs.get_phy_negotiated_link_rate()
            sas_ports_dict = sorted(sas_ports_dict.items(),
                                    key=lambda kv: int(kv[0].split(':')[1]))
            health = []
            if sas_ports_dict:
                for rid, rate in sas_ports_dict:
                    r_data["health"]["specifics"].append({
                        "resource_id": f"{sas_rid}:{rid.strip()}",
                        "negotiated_link_rate": rate.strip()
                    })
                    if "Gbit".lower() in rate.strip().lower():
                        health.append("OK")

            # By some logic set health status, description, recommendation
            health_data.append(health)
            health_status = "OK" if "OK" in health else "Fault"
            self.set_health_data(r_data, health_status)
            if r_data["health"]["specifics"]:
                sas_hba_data.append(r_data)

        if leaf_node == "sas_hba":
            return sas_hba_data

        sas_ports_data = []
        for heath_list in health_data:
            for i, health in enumerate(heath_list):
                if i % 4:
                    continue

                sas_port_data = self.get_data_template(f'sas_port_{i/4+1}',
                                                       False)
                sas_port_data["health"]["specifics"].append({
                    "negotiated_link_rate": "12.0 Gbit"
                })

                health_status = "OK" if "OK" in heath_list[i:i+4] else "Fault"
                self.set_health_data(sas_port_data, health_status)
                sas_ports_data.append(sas_port_data)

        return sas_ports_data

    def get_nw_ports_info(self):
        """Return the Network ports information."""
        network_cable_data = []
        io_counters = psutil.net_io_counters(pernic=True)

        for interface, addrs in psutil.net_if_addrs().items():
            nic_info = self.get_data_template(interface, False)

            specifics = {}
            for addr in addrs:
                if addr.family == socket.AF_INET:
                    specifics["ipV4"] = addr.address

            if interface in io_counters:
                io_info = io_counters[interface]
                specifics.update({
                    "networkErrors": io_info.errin + io_info.errout,
                    "droppedPacketsIn": io_info.dropin,
                    "droppedPacketsOut": io_info.dropout,
                    "packetsIn": io_info.packets_recv,
                    "packetsOut": io_info.packets_sent,
                    "trafficIn": io_info.bytes_recv,
                    "trafficOut": io_info.bytes_sent
                })

            nw_status, nw_cable_conn_status = \
                self.get_nw_status(interface)

            specifics["nwStatus"] = nw_status
            specifics["nwCableConnStatus"] = nw_cable_conn_status
            nic_info["health"]["specifics"].append(specifics)

            # set health status, description and recommendation
            map_status = {"UP": "OK", "DOWN": "Fault", "UNKNOWN": "UNKNOWN"}
            health_status = map_status[nw_cable_conn_status]

            self.set_health_data(nic_info, health_status)

            network_cable_data.append(nic_info)

        return network_cable_data

    def get_nw_status(self, interface):
        """Read & Return the latest network status from sysfs files."""
        try:
            nw_status = self.sysfs.fetch_nw_operstate(interface)
            nw_cable_conn_status = self.sysfs.fetch_nw_cable_status(
                self.sysfs.get_sys_dir_path('net'), interface
            )
        except Exception as err:
            raise ResourceMapError(errno.EINVAL,
                                   ("Unable to fetch network status due to"
                                    " an error: %s" % err))
        return nw_status, nw_cable_conn_status


# if __name__ == "__main__":
#     server = ServerMap()
#     health_data = server.get_health_info(rpath="nodes[0]>compute[0]")
#     print(health_data)
