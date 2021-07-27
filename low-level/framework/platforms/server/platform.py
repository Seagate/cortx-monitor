#!/usr/bin/python3

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
import errno

from cortx.utils.process import SimpleProcess
from framework.utils.ipmi_client import IpmiFactory
from framework.utils.service_logging import logger
from framework.base import sspl_constants as const
from framework.utils.conf_utils import (
    Conf, GLOBAL_CONF, SSPL_CONF, SERVICEMONITOR,
    MONITORED_SERVICES, EXCLUDED_SERVICES, NODE_TYPE_KEY)


class Platform:
    """provides information about server."""

    def __init__(self):
        """Initialize instance."""
        self._ipmi = IpmiFactory().get_implementor("ipmitool")

    @staticmethod
    def get_os_info():
        """Returns OS information from /etc/os-release."""
        os_release = ""
        os_info = {}
        with open("/etc/os-release") as f:
            os_release = f.read()
        if os_release:
            os_lst = os_release.split("\n")
            for line in os_lst:
                data = line.split('=')
                if len(data)>1 and data[1].strip() != "":
                    key = data[0].strip().lower().replace(" ","_")
                    value = data[1].strip().replace("\"","")
                    os_info.update({key: value})
        return os_info

    def get_bmc_info(self):
        """Returns node server bmc info."""
        bmc_info = {}
        cmd = "bmc info"
        out, _, retcode = self._ipmi._run_ipmitool_subcommand(cmd)
        if retcode == 0:
            out_lst = out.split("\n")
            for line in out_lst:
                data = line.split(':')
                if len(data)>1 and data[1].strip() != "":
                    key = data[0].strip().lower().replace(" ","_")
                    value = data[1].strip()
                    bmc_info.update({key: value})
        return bmc_info

    def get_server_details(self):
        """
        Returns a dictionary of server information.

        Grep 'FRU device description on ID 0' information using
        ipmitool command.
        """
        os_info = self.get_os_info()
        specifics = {
            "Board Mfg": "",
            "Board Product": "",
            "Board Part Number": "",
            "Product Name": "",
            "Product Part Number": "",
            "Manufacturer": self._ipmi.get_manufacturer_name(),
            "OS": os_info.get('id', '') + os_info.get('version_id', '')
            }
        cmd = "fru print"
        prefix = "FRU Device Description : Builtin FRU Device (ID 0)"
        search_res = ""
        out, _, retcode = self._ipmi._run_ipmitool_subcommand(cmd)
        if retcode == 0:
            # Get only 'FRU Device Description : Builtin FRU Device (ID 0)' information
            search_res = re.search(
                r"((.*%s[\S\n\s]+ID 1\)).*)|(.*[\S\n\s]+)" % prefix, out)
            search_res = search_res.group() if search_res else ""
        for key in specifics.keys():
            if key in search_res:
                device_desc = re.search(
                    r"%s[\s]+:[\s]+([\w-]+)(.*)" % key, out)
                if device_desc:
                    value = device_desc.groups()[0]
                specifics.update({key: value})
        return specifics

    @staticmethod
    def validate_server_type_support(log, Error, server_type):
        """Check for supported server type."""
        logger.debug(log.svc_log(f"Server Type:{server_type}"))
        if not server_type:
            msg = "ConfigError: server type is unknown."
            logger.error(log.svc_log(msg))
            raise Error(errno.EINVAL, msg)
        if server_type.lower() not in const.RESOURCE_MAP["server_type_supported"]:
            msg = f"{log.service} provider is not supported for server type '{server_type}'"
            logger.error(log.svc_log(msg))
            raise Error(errno.EINVAL, msg)

    def get_effective_monitored_services():
        """Get platform type based monitored services."""
        # Align node type as it is given in sspl.conf SERVICEMONITOR section
        node_type = Conf.get(GLOBAL_CONF, NODE_TYPE_KEY).lower()
        vm_types = ["virtual", "vm"]
        node_type = "vm" if node_type in vm_types else "hw"

        monitored_services = Conf.get(
            SSPL_CONF, f'{SERVICEMONITOR}>{MONITORED_SERVICES}', [])
        excluded_services = Conf.get(
            SSPL_CONF,
            f'{SERVICEMONITOR}>{EXCLUDED_SERVICES}>{node_type}', [])
        effective_monitored_services = list(
            set(monitored_services)-set(excluded_services))

        logger.debug("Monitored services list, %s" % monitored_services)
        logger.debug("Excluded monitored services list, " \
            "%s for environment %s" %(excluded_services, node_type))
        logger.debug("Effective monitored services list, " \
            "%s" % effective_monitored_services)

        return effective_monitored_services
