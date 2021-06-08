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
  Description: Storage class to provide fru health and specific information
               through controller web service.
 ***************************************************************************
"""

import errno
import json
import re
import time

from framework.utils.conf_utils import (
    GLOBAL_CONF, SRVNODE, Conf, STORAGE_TYPE_KEY, NODE_TYPE_KEY, SITE_ID_KEY,
    RACK_ID_KEY, NODE_ID_KEY, CLUSTER_ID_KEY, RELEASE, TARGET_BUILD)
from error import HealthProviderError
from resource_health import ResourceHealth


class StorageHealth(ResourceHealth):
    """Provides health information of FRUs in storage"""

    name = "storage"

    def __init__(self):
        """Initialize storage"""
        super().__init__()
        self.validate_storage_type_support()
        self.storage_frus = {
            "controllers": self.get_controllers_info
            }

    @staticmethod
    def validate_storage_type_support():
        """Check for supported storage type"""
        storage_type = Conf.get(GLOBAL_CONF, STORAGE_TYPE_KEY, "virtual").lower()
        supportted_types = ["5u84", "rbod", "pods"]
        if storage_type not in supportted_types:
            raise HealthProviderError(
                errno.EINVAL,
                "Health provider is not supported for storage type '%s'." % storage_type)

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

    def get_health_info(self, rpath):
        """
        Fetch health information for given FRU
        rpath: Resouce path (Example: hw>controllers)
        """
        info = {}
        nodes = rpath.strip().split(">")
        leaf_node, _ = self.get_node_details(nodes[-1])
        if leaf_node == "storage":
            info["last_updated"] = int(time.time())
            for fru in self.storage_frus:
                info.update({fru: self.storage_frus[fru]()})
        else:
            fru = None
            fru_found = False
            for node in nodes:
                fru, _ = self.get_node_details(node)
                if self.storage_frus.get(fru):
                    fru_found = True
                    info = self.storage_frus[fru]()
                    break
        if not fru_found:
            raise HealthProviderError(
                errno.EINVAL,
                "Health provider doesn't have support for'{rpath}'.")
        return info

    def get_controllers_info(self):
        """Update and return controller information in specific format"""
        data = []
        controllers = self.get_realstor_show_data("controllers")
        for controller in controllers:
            controller_dict = {
              "uid": controller.get("durable-id"),
              "fru": "true",
              "last_updated": int(time.time()),
              "health": {
                "status": controller.get("health", "NA"),
                "description": controller.get("description"),
                "recommendation": controller.get("health-recommendation"),
                "specifics": [
                  {
                    "serial-number": controller.get("serial-number", "NA"),
                    "disks": controller.get("disks", "NA"),
                    "virtual-disks": controller.get("virtual-disks", "NA"),
                    "model": controller.get("model", "NA"),
                    "part-number": controller.get("part-number", "NA"),
                    "fw": controller.get("sc-fw", "NA"),
                    "location": controller.get("position", "NA")
                  }
                ]
              }
            }
            data.append(controller_dict)
        return data

    @staticmethod
    def get_realstor_show_data(fru: str):
        """Fetch fru information through webservice API"""
        from framework.platforms.realstor.realstor_enclosure import (
            singleton_realstorencl as ENCL)

        fru_data = []
        fru_uri_map = {
            "controllers": ENCL.URI_CLIAPI_SHOWCONTROLLERS
        }
        url = ENCL.build_url(fru_uri_map.get(fru))
        response = ENCL.ws_request(url, ENCL.ws.HTTP_GET)

        if not response or response.status_code != ENCL.ws.HTTP_OK:
            return []
        elif response or response.status_code == ENCL.ws.HTTP_OK:
            response_data = json.loads(response.text)
            fru_data = response_data.get(fru)

        return fru_data

if __name__ == "__main__":
    storage = StorageHealth()
    health_data = storage.get_health_info(rpath="nodes[0]>storage[0]>hw>controllers")
    print(health_data)
