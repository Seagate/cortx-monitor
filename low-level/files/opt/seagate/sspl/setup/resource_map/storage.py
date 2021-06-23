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
  Description: StorageMap class provides resource map and related information
               like health, manifest, etc,.
 ***************************************************************************
"""

import errno
import json
import re
import time

from framework.utils.conf_utils import (
    GLOBAL_CONF, SRVNODE, Conf, STORAGE_TYPE_KEY, NODE_TYPE_KEY, SITE_ID_KEY,
    RACK_ID_KEY, NODE_ID_KEY, CLUSTER_ID_KEY, RELEASE, TARGET_BUILD)
from error import ResourceMapError
from resource_map import ResourceMap
from framework.base.sspl_constants import HEALTH_UNDESIRED_VALS


class StorageMap(ResourceMap):
    """Provides storage resource related information."""

    name = "storage"

    def __init__(self):
        """Initialize storage."""
        super().__init__()
        self.validate_storage_type_support()
        self.storage_frus = {
            "controllers": self.get_controllers_info,
            "psus": self.get_psu_info,
            "platform_sensors": self.get_platform_sensors_info,
            "logical_volumes": self.get_logical_volumes_info,
            "disk_groups": self.get_disk_groups_info
        }

    @staticmethod
    def validate_storage_type_support():
        """Check for supported storage type."""
        storage_type = Conf.get(GLOBAL_CONF, STORAGE_TYPE_KEY, "virtual").lower()
        supported_types = ["5u84", "rbod", "pods", "corvault"]
        if storage_type not in supported_types:
            raise ResourceMapError(
                errno.EINVAL,
                "Health provider is not supported for storage type '%s'." % storage_type)

    def get_health_info(self, rpath):
        """
        Fetch health information for given FRU.

        rpath: Resouce path (Example: nodes[0]>storage[0]>hw>controllers)
        """
        info = {}
        fru_found = False
        nodes = rpath.strip().split(">")
        leaf_node, _ = self.get_node_details(nodes[-1])
        if leaf_node == "storage":
            for fru in self.storage_frus:
                info.update({fru: self.storage_frus[fru]()})
            info["last_updated"] = int(time.time())
            fru_found = True
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
            raise ResourceMapError(
                errno.EINVAL,
                "Health provider doesn't have support for'{rpath}'.")
        return info

    def get_controllers_info(self):
        """Update and return controller information in specific format"""
        data = []
        controllers = self.get_realstor_encl_data("controllers")
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

    def get_psu_info(self):
        """Update and return PSUs information in specific format."""
        data = []
        psus = self.get_realstor_encl_data("power-supplies")
        for psu in psus:
            psu_dict = {
              "uid": psu.get("durable-id"),
              "fru": "true",
              "last_updated": int(time.time()),
              "health": {
                "status": psu.get("health", "NA"),
                "description": psu.get("description"),
                "recommendation": psu.get("health-recommendation"),
                "specifics": [
                  {
                    "location": psu.get("location", "NA"),
                    "dc12v": psu.get("dc12v", "NA"),
                    "dc5v": psu.get("dc5v", "NA"),
                    "dc33v": psu.get("dc33v", "NA"),
                    "dc12i": psu.get("dc12i", "NA"),
                    "dc5i": psu.get("dc5i", "NA"),
                    "dctemp": psu.get("dctemp", "NA")
                  }
                ]
              }
            }
            data.append(psu_dict)
        return data

    def get_platform_sensors_info(self):
        sensor_list = ['temperature', 'current', 'voltage']
        sensor_data = self.build_encl_platform_sensors_data(sensor_list)
        return sensor_data

    def build_encl_platform_sensors_data(self, platform_sensors):
        """Builds and returns platform sensors data (Temperature, Voltage and Current)

        It calls enclosure API to fetch the sensor data.

        Args:
            platform_sensors - list of sensors to fetch the data.
        Returns:
            dict with three keys for respective sensors.
        """
        sensors_data = {}
        sensors_resp = self.get_realstor_encl_data('sensor-status')
        if sensors_resp:
            for platform_sensor in platform_sensors:
                for sensor in sensors_resp['api-response']['sensors']:
                    if sensor['sensor-type'].lower() == platform_sensor:
                        single_sensor_data = {
                          'uid': sensor.get('durable-id'),
                          'fru': 'false',
                          'last_updated':  int(time.time()),
                          'health': {
                            'status': sensor.get('status'),
                            'description': sensor.get("description", "NA"),
                            'recommendation': sensor.get("recommendation", "NA"),
                            'specifics': [
                              {
                                'sensor-name': sensor.get('sensor-name'),
                                'value': sensor.get('value'),
                                'controller-id': sensor.get('controller-id'),
                                'container': sensor.get('container'),
                              }
                            ]
                          }
                        }
                        if platform_sensor in sensors_data:
                            sensors_data[platform_sensor].append(single_sensor_data)
                        else:
                            sensors_data[platform_sensor] = [single_sensor_data]
        return sensors_data

    def get_logical_volumes_info(self):
        """Update and return logical volume information in specific format."""
        logvol_data = []
        logicalvolumes = self.get_realstor_encl_data("volumes")
        if logicalvolumes:
            for logicalvolume in logicalvolumes:
                health = logicalvolume.get("health", "NA")
                if health in HEALTH_UNDESIRED_VALS:
                    health = "NA"
                logvol_data.append({
                    "uid": logicalvolume.get("volume-name", "NA"),
                    "fru": False,
                    "last_updated": int(time.time()),
                    "health": {
                        "status": health,
                        "description": logicalvolume.get("volume-description", "NA"),
                        "recommendation": logicalvolume.get("health-recommendation", "NA"),
                        "specifics": [
                            {
                                "disk_group": {
                                    "disk_group_name": logicalvolume.get("container-name", "NA"),
                                    "pool_serial_number": logicalvolume.get("container-serial", "NA")
                                }
                            }
                        ]
                    }
                })
        return logvol_data

    def get_disk_groups_info(self):
        """Update and return disk-group information in specific format."""
        dg_data = []
        dg_vol_map = {}
        diskgroups = self.get_realstor_encl_data("disk-groups")
        # Mapping logical volumes with disk group.
        logicalvolumes = self.get_realstor_encl_data("volumes")
        if logicalvolumes:
            for logicalvolume in logicalvolumes:
                volume_pool_sr_no = logicalvolume.get("container-serial", "NA")
                volume_uid = logicalvolume.get("volume-name", "NA")
                if volume_pool_sr_no in dg_vol_map:
                    dg_vol_map[volume_pool_sr_no].append({"volume_uid": volume_uid})
                else:
                    dg_vol_map.update({volume_pool_sr_no:[{"volume_uid": volume_uid}]})
        dg_description = "Disk group is in good health."
        if diskgroups:
            for diskgroup in diskgroups:
                health = diskgroup.get("health", "NA")
                pool_sr_no = diskgroup.get("pool-serial-number", "NA")
                if pool_sr_no in dg_vol_map:
                    volumes = dg_vol_map[pool_sr_no]
                else:
                    volumes = None
                if health in HEALTH_UNDESIRED_VALS:
                    health = "NA"
                    dg_description = "Disk group is in unknown health state."
                dg_data.append({
                    "uid": diskgroup.get("name", "NA"),
                    "fru": False,
                    "last_updated": int(time.time()),
                    "health": {
                        "status": health,
                        "description": dg_description,
                        "recommendation": diskgroup.get("health-recommendation", "NA"),
                        "specifics": [
                            {
                                "class": diskgroup.get("storage-type", "NA"),
                                "disks": diskgroup.get("diskcount", "NA"),
                                "size": diskgroup.get("size", "NA"),
                                "free": diskgroup.get("freespace", "NA"),
                                "status": diskgroup.get("status", "NA"),
                                "current_job": diskgroup.get("current-job", "NA"),
                                "current_job_completion": diskgroup.get(
                                    "current-job-completion", "NA"),
                                "tier": diskgroup.get("storage-tier", "NA"),
                                "pool": diskgroup.get("pool", "NA"),
                                "blocksize": diskgroup.get("blocksize", "NA"),
                                "chunksize": diskgroup.get("chunksize", "NA"),
                                "volumes": volumes
                            }
                        ]
                    }
                })
        return dg_data

    @staticmethod
    def get_realstor_encl_data(fru: str):
        """Fetch fru information through webservice API."""
        from framework.platforms.realstor.realstor_enclosure import (
            singleton_realstorencl as ENCL)

        fru_data = []
        fru_uri_map = {
            "controllers": ENCL.URI_CLIAPI_SHOWCONTROLLERS,
            "power-supplies": ENCL.URI_CLIAPI_SHOWPSUS,
            "platform_sensors": ENCL.URI_CLIAPI_SHOWSENSORSTATUS,
            "volumes": ENCL.URI_CLIAPI_SHOWVOLUMES,
            "disk-groups": ENCL.URI_CLIAPI_SHOWDISKGROUPS
        }
        url = ENCL.build_url(fru_uri_map.get(fru))
        response = ENCL.ws_request(url, ENCL.ws.HTTP_GET)

        if not response or response.status_code != ENCL.ws.HTTP_OK:
            return []
        elif response or response.status_code == ENCL.ws.HTTP_OK:
            response_data = json.loads(response.text)
            fru_data = response_data.get(fru)

        return fru_data


# if __name__ == "__main__":
#     storage = StorageMap()
#     frus = ["controllers", "psus"]
#     for fru in frus:
#         rpath = f"nodes[0]>storage[0]>hw>{fru}"
#         health_data = storage.get_health_info(rpath=rpath)
#         print(health_data)
#     volume_health_data = storage.get_health_info(rpath="nodes[0]>storage[0]>fw>logical_volumes")
#     dg_health_data = storage.get_health_info(rpath="nodes[0]>storage[0]>fw>disk_groups")
#     print(json.dumps(volume_health_data))
#     print(json.dumps(dg_health_data))
