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

import os

from framework.utils.conf_utils import (
    Conf, SSPL_CONF, SYSFS_PATH, SYSTEM_INFORMATION)
from framework.platforms.server.error import InterfaceError


class SAS:
    """The Class provides access to the SAS interface information."""

    name = "SAS"

    def __init__(self):
        """Initialize the class."""
        sysfs_dir = Conf.get(SSPL_CONF,
                             f'{SYSTEM_INFORMATION}>{SYSFS_PATH}')
        self.base_dir = os.path.join(sysfs_dir, 'class')

    def get_host_list(self):
        """
            Return SAS host list from /sys/class/sas_host directory.
            eg: ['host1', 'host2']
        """
        try:
            host_dirpath = os.path.join(self.base_dir, 'sas_host')
            sas_hosts = os.listdir(host_dirpath)
            sas_hosts = [host for host in sas_hosts
                         if 'host' in host]
        except OSError as err:
            err_no, err_str = err.args
            raise InterfaceError(
                err_no, "Failed to get sas host list due to '%s'", err_str)
        return sas_hosts

    def get_port_list(self, host=""):
        """
            Return a list of SAS ports.
            searches for ports from given host in /sys/class/sas_port
            directory if directory exists else return an empty list.
            eg: ['port-1:0', 'port-1:1', 'port-1:2', 'port-1:3']
        """
        try:
            host_id = host.replace('host', '')
            port_dirpath = os.path.join(self.base_dir, 'sas_port')
            sas_ports = os.listdir(port_dirpath)
            sas_ports = [port for port in sas_ports
                         if f'port-{host_id}' in port]
        except OSError as err:
            err_no, err_str = err.args
            raise InterfaceError(
                err_no, "Failed to get sas port list due to '%s'", err_str)
        return sas_ports

    def get_port_data(self, port_name):
        """
            Return SAS port data/info of given port.
            eg: Given input port-1:0 returns
                { "port_id":"sas_port-1:0",
                  "state":"running",
                  "sas_address":"0x500c0fff0a98b000"
                }
        """
        try:
            host_id, port_id = port_name.replace('port-', '').split(':')
            port_data_path = os.path.join(
                             self.base_dir, 'sas_end_device',
                             f'end_device-{host_id}:{port_id}',
                             f'device/target{host_id}:0:{port_id}',
                             f'{host_id}:0:{port_id}:0')
            with open(os.path.join(port_data_path, 'state')) as cFile:
                state = cFile.read().strip()

            with open(os.path.join(port_data_path, 'sas_address')) as cFile:
                sas_addr = cFile.read().strip()

            port_data = {
                    "port_id": f'sas_{port_name}',
                    "state": state,
                    "sas_address": sas_addr
                }
        except OSError as err:
            err_no, err_str = err.args
            raise InterfaceError(
                err_no, "Failed to get sas port data due to '%s'", err_str)
        return port_data

    def get_phy_list_for_port(self, port):
        """
            Return list of SAS phys under given port.
            eg: for given port-1:0 it might return
                [ 'phy-1:0', 'phy-1:1', 'phy-1:2', 'phy-1:3']
                returns an empty list if port-1:0 does not exist.
        """
        try:
            phy_list_dir = os.path.join(
                            self.base_dir, 'sas_port',
                            port, 'device')
            phys = os.listdir(phy_list_dir)
            phys = [phy for phy in phys if 'phy' in phy]
            phys.sort(key=lambda phy: int(phy.split(':')[1]))
        except OSError as err:
            err_no, err_str = err.args
            raise InterfaceError(
                err_no, "Failed to get sas phy list due to '%s'", err_str)
        return phys

    def get_phy_data(self, phy):
        """
            Return SAS phy information.
            eg: for phy `phy-1:8` it might return
                {
                    "phy_id":"phy-1:8",
                    "state":"enabled",
                    "negotiated_linkrate":"12.0 Gbit"
                }
        """
        try:
            phy_data_dir = os.path.join(
                            self.base_dir, 'sas_phy', phy)

            with open(os.path.join(phy_data_dir, 'enable')) as cFile:
                state = cFile.read().strip()
                state = "enabled" if state == '1' else "disabled"

            with open(os.path.join(phy_data_dir, 'negotiated_linkrate')) as cFile:
                n_link_rate = cFile.read().strip()

            phy_data = {
                "phy_id": phy,
                "state": state,
                "negotiated_linkrate": n_link_rate
            }
        except OSError as err:
            err_no, err_str = err.args
            raise InterfaceError(
                err_no, "Failed to get sas phy data due to '%s'", err_str)
        return phy_data
