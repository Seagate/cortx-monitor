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


class Platform:
    """provides information about server."""

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

    @staticmethod
    def get_manufacturer_name():
        """Returns node server manufacturer name."""
        manufacturer = ""
        cmd = "ipmitool bmc info"
        res_op, _, res_rc = SimpleProcess(cmd).run()
        if isinstance(res_op, bytes):
            res_op = res_op.decode("utf-8")
        if res_rc == 0:
            search_res = re.search(
                r"Manufacturer Name[\s]+:[\s]+([\w]+)(.*)", res_op)
            if search_res:
                manufacturer = search_res.groups()[0]
        return manufacturer

    @staticmethod
    def get_server_details():
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
            "Manufacturer": Platform.get_manufacturer_name(),
            "OS": Platform.get_os()
            }
        cmd = "ipmitool fru print"
        prefix = "FRU Device Description : Builtin FRU Device (ID 0)"
        search_res = ""
        res_op, _, res_rc = SimpleProcess(cmd).run()
        if isinstance(res_op, bytes):
            res_op = res_op.decode("utf-8")
        if res_rc == 0:
            # Get only 'FRU Device Description : Builtin FRU Device (ID 0)' information
            search_res = re.search(r"((.*%s[\S\n\s]+ID 1\)).*)|(.*[\S\n\s]+)" % prefix, res_op)
            if search_res:
                search_res = search_res.group()
        for key in specifics.keys():
            if key in search_res:
                device_desc = re.search(r"%s[\s]+:[\s]+([\w-]+)(.*)" % key, res_op)
                if device_desc:
                    value = device_desc.groups()[0]
                specifics.update({key: value})
        return specifics
