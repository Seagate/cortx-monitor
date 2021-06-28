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
import time
from abc import ABCMeta, abstractmethod

from framework.base.sspl_constants import DEFAULT_RECOMMENDATION
from framework.utils.service_logging import init_logging
from framework.utils.conf_utils import ( SSPL_CONF, Conf,
    SYSTEM_INFORMATION, LOG_LEVEL)


class ResourceMap(metaclass=ABCMeta):
    """Abstract class for all other resource types."""

    name = "resource"

    def __init__(self):
        """Initialize resource."""
        logging_level = Conf.get(SSPL_CONF,
            f"{SYSTEM_INFORMATION}>{LOG_LEVEL}", "INFO")
        init_logging('node-health', logging_level)

    @abstractmethod
    def get_health_info(self, rpath):
        """
        Get health information of fru in given resource id.

        rpath: Resource id (Example: hw>disks)
        """
        pass

    @staticmethod
    def get_node_details(node):
        """
        Parse node information and returns left string and instance.
        Example
            "storage"    -> ("storage", "*")
            "storage[0]" -> ("storage", "0")

            "compute"    -> ("compute", "*")
            "compute[0]" -> ("compute", "0")
        """
        res = re.search(r"(\w+)\[([\d]+)\]|(\w+)", node)
        inst = res.groups()[1] if res.groups()[1] else "*"
        node = res.groups()[0] if res.groups()[1] else res.groups()[2]
        return node, inst

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
                        recommendation=None, specifics=None, resource=""):
        """Sets health attributes for a component."""
        good_state = (status == "OK")
        if not description:
            description = "%s %s %s in good health." % (
                resource,
                health_data.get("uid"),
                'is' if good_state else 'is not')
        if not recommendation:
            recommendation = 'NA' if good_state\
                else DEFAULT_RECOMMENDATION
        health_data["last_updated"] = int(time.time())
        health_data["health"].update({
            "status": status,
            "description": description,
            "recommendation": recommendation,
            "specifics": specifics
        })
