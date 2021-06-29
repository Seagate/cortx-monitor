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

import re

from cortx.utils.process import SimpleProcess
from framework.utils.ipmi_client import IpmiFactory


class Platform:
    """provides information about server."""

    def __init__(self):
        self._ipmi = IpmiFactory().get_implementor("ipmitool")

    @staticmethod
    def get_os():
        """Returns os name({ID}{VERSION_ID}) from /etc/os-release."""
        os_release = ""
        with open("/etc/os-release") as f:
            os_release = f.read()
        if os_release:
            os_id = re.findall(
                '^ID=(.*)\n', os_release, flags=re.MULTILINE)
            os_version_id = re.findall(
                '^VERSION_ID=(.*)\n', os_release, flags=re.MULTILINE)
            if os_id and os_version_id:
                os_info = [os_str.strip('"') for os_str in os_id+os_version_id]
                return "".join(os_info)
        return os_release

    def get_manufacturer_name(self):
        """Returns node server manufacturer name."""
        manufacturer = ""
        cmd = "bmc info"
        out, _, retcode = self._ipmi._run_ipmitool_subcommand(cmd)
        if retcode == 0:
            search_res = re.search(
                r"Manufacturer Name[\s]+:[\s]+([\w]+)(.*)", out)
            if search_res:
                manufacturer = search_res.groups()[0]
        return manufacturer

    def get_server_details(self):
        """Returns a dictionary of server information.

        Grep 'FRU device description on ID 0' information using
        ipmitool command.
        """
        specifics = {
            "Board Mfg": "",
            "Board Product": "",
            "Board Part Number": "",
            "Product Name": "",
            "Product Part Number": "",
            "Manufacturer": self.get_manufacturer_name(),
            "OS": self.get_os()
            }
        cmd = "fru print"
        prefix = "FRU Device Description : Builtin FRU Device (ID 0)"
        search_res = ""
        out, _, retcode = self._ipmi._run_ipmitool_subcommand(cmd)
        if retcode == 0:
            # Get only 'FRU Device Description : Builtin FRU Device (ID 0)' information
            search_res = re.search(
                r"((.*%s[\S\n\s]+ID 1\)).*)|(.*[\S\n\s]+)" % prefix, out)
            if search_res:
                search_res = search_res.group()
        for key in specifics.keys():
            if key in search_res:
                device_desc = re.search(
                    r"%s[\s]+:[\s]+([\w-]+)(.*)" % key, out)
                if device_desc:
                    value = device_desc.groups()[0]
                specifics.update({key: value})
        return specifics
