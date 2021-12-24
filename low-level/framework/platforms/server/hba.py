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
from framework.platforms.server.error import HBAError
from framework.utils.os_utils import OSUtils
from framework.utils.tool_factory import ToolFactory
from framework.base import sspl_constants as const
from cortx.utils.process import SimpleProcess, PipedProcess


class HBA:
    """The class provides access to the HBA interface information."""

    name = "HBA"

    def __init__(self):
        """Initialize the class."""

        self.__utility = None
        self.host_type = OSUtils.get_host_type() or None
        self.detected = False

        # TODO: Virtual memory may get exhausted by running scan command.
        # Scanning may take long time. To avoid sensor polling overlapping,
        # scan finish time must be known. HBA Sensor polling interval must
        # be greater than scan finish time.
        # Rescan multipath
        #self._rescan_scsi_bus()
        self.host_data = {
            const.FC_HOST: self._get_fc_host_data,
            const.SCSI_HOST: self._get_scsi_host_data
        }


    @staticmethod
    def _rescan_scsi_bus():
        """Scan and detect new LUNs."""

        _, err, rc = SimpleProcess("rescan-scsi-bus.sh").run()
        if rc != 0:
            raise HBAError(rc, "Failed to scan scsi bus due to %s", err)


    def _get_model_vendor(self):
        """Returns model and vendor name of HBA."""

        model = vendor = ""
        cmd = ""

        if self.host_type == const.FC_HOST:
            cmd = "lspci | grep -Ei 'Fibre Channel'"
        elif self.host_type == const.SCSI_HOST:
            cmd = "lspci | grep -Ei 'Serial Attached SCSI|SAS|LSI|SCSI storage controller'"

        out, _, rc = PipedProcess(cmd).run()
        if rc == 0:
            model, vendor = out.decode().split(": ")

        return model, vendor


    def _is_host_found(self, host):
        """
        Check host is present.

        Parameters:
            host (str): scsi/fc host
        """

        if host not in self.get_hosts():
            return False
        return True


    def _get_scsi_host_data(self, host):
        """
        Returns SCSI host information.

        Parameters:
            host (str): scsi host detected by HBA card
        Returns:
            data (dict): scsi host information
        """

        data = {}

        if self._is_host_found(host):
            data = {
                "port_id": self.__utility.get_host_data(host, 'unique_id'),
                "state": self.__utility.get_host_data(host, 'state'),
                "active_mode": self.__utility.get_host_data(host, 'active_mode'),
                "host_busy": self.__utility.get_host_data(host, 'host_busy')
                }

        return data


    def _get_fc_host_data(self, host):
        """
        Returns FC host information.

        Parameters:
            host (str): scsi host detected by HBA card
        Returns:
            data (dict): fc host information
        """

        data = {}

        if self._is_host_found(host):
            data = {
                "port_id": self.__utility.get_host_data(host, 'port_name'),
                "state": self.__utility.get_host_data(host, 'port_state')
                }

        return data


    def initialize_utility(self, utility):
        """Invoke HBA card utility tool."""

        self.__utility = ToolFactory().get_instance(utility)


    def get_hosts(self):
        """Returns hosts detected by HBA card."""

        hosts = self.__utility.get_host_list()

        # Refresh host type
        self.host_type = self.__utility.host_type
        self.detected = True if self.host_type else False

        return hosts


    def get_host_data(self, host):
        """
        Returns host information based on its type.

        Parameters:
            host (str): scsi/fc host detected by HBA card
        Returns:
            data (dict): host information
        """

        data = {}

        if self.host_data.get(self.host_type):
            data = self.host_data[self.host_type](host)

        return data
