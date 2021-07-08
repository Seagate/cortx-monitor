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
  Description: Storage class provides manifest information like technical
  information of storage/enclosure components etc,.
 ***************************************************************************
"""

import errno
import time

from framework.utils.conf_utils import GLOBAL_CONF, Conf, STORAGE_TYPE_KEY
from error import ManifestError
from resource_map import CortxManifest
from framework.base.sspl_constants import MANIFEST_SVC_NAME
from framework.utils.service_logging import CustomLog, logger
from framework.platforms.realstor.realstor_enclosure import (
    singleton_realstorencl as ENCL)
from framework.utils.utility import Utility


class StorageManifest(CortxManifest):
    """Provides storage manifest related information."""

    name = "storage_manifest"

    def __init__(self):
        """Initialize storage."""
        super().__init__()
        self.log = CustomLog(MANIFEST_SVC_NAME)
        storage_type = Conf.get(GLOBAL_CONF, STORAGE_TYPE_KEY)
        Utility.validate_storage_type_support(self.log, ManifestError, storage_type)
        hw_resources = {
            "enclosures": self.get_enclosures_info,
            "controllers": self.get_controllers_info,
            "power-supplies": self.get_psu_info,
            "fan-modules": self.get_fan_modules_info,
            "disks": self.get_drives_info,
            "sideplane": self.get_sideplane_expander_info
        }
        fw_resources = {
            "versions": self.get_versions_info,
        }
        self.storage_resources = {
            "hw": hw_resources,
            "fw": fw_resources
        }

    def get_manifest_info(self, rpath):
        """
        Fetch Manifest information for given rpath.
        """
        logger.info(self.log.svc_log(
            f"Get Manifest data for rpath:{rpath}"))
        info = {}
        resource_found = False
        nodes = rpath.strip().split(">")
        leaf_node, _ = Utility.get_node_details(nodes[-1])

        # Fetch health information for all sub nodes
        if leaf_node == "storage":
            resource_found = True
            info = self.get_storage_manifest_info()
        elif leaf_node in self.storage_resources:
            resource_found = True
            for resource, method in self.storage_resources[leaf_node].items():
                try:
                    info.update({resource: method()})
                    resource_found = True
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}:{err}"))
                    info = None
        else:
            for node in nodes:
                resource, _ = Utility.get_node_details(node)
                for res_type in self.storage_resources:
                    method = self.storage_resources[res_type].get(resource)
                    if not method:
                        logger.error(
                            self.log.svc_log(
                                f"No mapping function found for {res_type}"))
                        continue
                    try:
                        resource_found = True
                        info = method()
                        break
                    except Exception as err:
                        logger.error(
                            self.log.svc_log(f"{err.__class__.__name__}: {err}"))
                        info = None

                if resource_found:
                    break

        if not resource_found:
            msg = f"Invalid rpath or manifest provider doesn't have support for'{rpath}'."
            logger.error(self.log.svc_log(f"{msg}"))
            raise ManifestError(errno.EINVAL, msg)

        return info

    def get_storage_manifest_info(self):
        """Get storage enclosure information."""
        storage = []
        info = {}
        for res_type in self.storage_resources:
            info.update({res_type: {}})
            for fru, method in self.storage_resources[res_type].items():
                try:
                    info[res_type].update({fru: method()})
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}: {err}"))
                    info[res_type].update({fru: None})
        info["last_updated"] = int(time.time())
        storage.append(info)
        return storage

    def get_enclosures_info(self):
        """Update and return enclosure information in specific format."""
        data = []
        chassis_serial_no = "NA"
        enclosure = ENCL.get_realstor_encl_data("enclosures")
        frus = ENCL.get_realstor_encl_data("frus")
        if frus:
            for fru in frus:
                if fru["name"] == "CHASSIS_MIDPLANE":
                    chassis_serial_no = fru.get("serial-number", "NA")
                    break
        for encl in enclosure:
            encl_dict = {
                "uid": encl.get("durable-id", "NA"),
                "type": encl.get("type", "NA"),
                "description": encl.get("description", "NA"),
                "product": encl.get("object-name", "NA"),
                "manufacturer": encl.get("vendor", "NA"),
                "serial_number": chassis_serial_no,
                "version": "NA",
                "part_number": encl.get("part-number", "NA"),
                "last_updated": int(time.time()),
                "specifics": [{
                    "enclosure_wwn": encl.get("enclosure-wwn", "NA"),
                    "platform": encl.get("platform-type", "NA"),
                    "board_model": encl.get("board-model", "NA"),
                    "mfg_date": encl.get("mfg-date", "NA"),
                    "number_of_disks": encl.get("number-of-disks", "NA"),
                    "number_of_power_supplies": encl.get("number-of-power-supplies", "NA"),
                    "model": encl.get("model", "NA"),
                    "columns": encl.get("columns", "NA"),
                    "slots": encl.get("slots", "NA"),
                    "midplane_type": encl.get("midplane-type", "NA"),
                    "enclosure_power": encl.get("enclosure-power", "NA"),
                }]
            }
            data.append(encl_dict)
            logger.debug(self.log.svc_log(
                f"Enclosure Manifest Data:{data}"))
        return data

    def get_controllers_info(self):
        """Update and return controller information in specific format."""
        data = []
        controllers = ENCL.get_realstor_encl_data("controllers")
        for controller in controllers:
            controller_dict = {
                "uid": controller.get("durable-id", "NA"),
                "type": controller.get("type", "NA"),
                "description": controller.get("description", "NA"),
                "product": controller.get("object-name", "NA"),
                "manufacturer": controller.get("vendor", "NA"),
                "serial_number": controller.get("serial-number", "NA"),
                "version": controller.get("hardware-version", "NA"),
                "part_number": controller.get("part-number", "NA"),
                "last_updated": int(time.time()),
                "specifics": [{
                    "disks": controller.get("disks", "NA"),
                    "virtual_disks": controller.get("virtual-disks", "NA"),
                    "host_ports": controller.get("host-ports", "NA"),
                    "drive_channels": controller.get("drive-channels", "NA"),
                    "drive_bus_type": controller.get("drive-bus-type", "NA"),
                    "fw": controller.get("sc-fw", "NA"),
                    "model": controller.get("model", "NA"),
                    "mfg_date": controller.get("mfg-date", "NA"),
                    "status": controller.get("status", "NA")
                }]
            }
            data.append(controller_dict)
            logger.debug(self.log.svc_log(
                f"Controller Manifest Data:{data}"))
        return data

    def get_psu_info(self):
        """Update and return power supplies information in specific format."""
        data = []
        psus = ENCL.get_realstor_encl_data("power-supplies")
        for psu in psus:
            psu_dict = {
                "uid": psu.get("durable-id", "NA"),
                "type": psu.get("type", "NA"),
                "description": psu.get("description", "NA"),
                "product": psu.get("object-name", "NA"),
                "manufacturer": psu.get("vendor", "NA"),
                "serial_number": psu.get("serial-number", "NA"),
                "version": psu.get("hardware-version", "NA"),
                "part_number": psu.get("part-number", "NA"),
                "last_updated": int(time.time()),
                "specifics": [{
                    "location": psu.get("location", "NA"),
                    "dc12v": psu.get("dc12v", "NA"),
                    "dc5v": psu.get("dc5v", "NA"),
                    "dc33v": psu.get("dc33v", "NA"),
                    "dc12i": psu.get("dc12i", "NA"),
                    "dc5i": psu.get("dc5i", "NA"),
                    "model": psu.get("model", "NA"),
                    "status": psu.get("status", "NA"),
                    "mfg_date": psu.get("mfg-date", "NA")
                }]
            }
            data.append(psu_dict)
            logger.debug(self.log.svc_log(
                f"PSU Manifest Data:{data}"))
        return data

    def get_drives_info(self):
        """Update and return drives information in specific format."""
        data = []
        drives = ENCL.get_realstor_encl_data("drives")
        for drive in drives:
            slot = drive.get("slot", -1)
            if slot == -1:
                continue
            drive_dict = {
                "uid": drive.get("durable-id", "NA"),
                "type": drive.get("type", "NA"),
                "description": drive.get("description", "NA"),
                "product": drive.get("object-name", "NA"),
                "manufacturer": drive.get("vendor", "NA"),
                "serial_number": drive.get("serial-number", "NA"),
                "version": drive.get("hardware-version", "NA"),
                "part_number": drive.get("part-number", "NA"),
                "last_updated": int(time.time()),
                "specifics": [{
                    "drive-serial-number": drive.get("serial-number")[:8],
                    "model": drive.get("model", "NA"),
                    "slot": slot,
                    "architecture": drive.get("architecture", "NA"),
                    "interface": drive.get("interface", "NA"),
                    "usage": drive.get("usage", "NA"),
                    "current_job_completion": drive.get("current-job-completion", "NA"),
                    "speed": drive.get("speed", "NA"),
                    "size": drive.get("size", "NA"),
                    "enclosure_wwn": drive.get("enclosure-wwn", "NA"),
                    "status": drive.get("status", "NA"),
                    "ssd_life_left": drive.get("ssd-life-left", "NA"),
                    "led_status": drive.get("led-status", "NA"),
                    "temperature": drive.get("temperature", "NA"),
                    "location": drive.get("location", "NA")
                }]
            }
            data.append(drive_dict)
            logger.debug(self.log.svc_log(
                f"Drive Manifest Data:{data}"))
        return data

    @staticmethod
    def get_fan_specfics(fan):
        return {
            "uid": fan.get("durable-id", "NA"),
            "type": fan.get("type", "NA"),
            "description": fan.get("description", "NA"),
            "product": fan.get("object-name", "NA"),
            "manufacturer": fan.get("vendor", "NA"),
            "serial_number": fan.get("serial-number", "NA"),
            "version": fan.get("hardware-version", "NA"),
            "part_number": fan.get("part-number", "NA"),
            "specifics": [{
                "status": fan.get("status", "NA"),
                "speed": fan.get("speed", "NA"),
                "location": fan.get("location", "NA")
            }]
        }

    def get_fan_modules_info(self):
        """Update and return fan modules information in specific format."""
        data = []
        fanmoduels_data = ENCL.get_realstor_encl_data("fan-modules")
        if fanmoduels_data:
            for fan_module in fanmoduels_data:
                fan_module_resp = {
                    "uid": fan_module.get("durable-id", "NA"),
                    "type": fan_module.get("type", "NA"),
                    "description": fan_module.get("description", "NA"),
                    "product": fan_module.get("object-name", "NA"),
                    "manufacturer": fan_module.get("vendor", "NA"),
                    "serial_number": fan_module.get("serial-number", "NA"),
                    "version": fan_module.get("hardware-version", "NA"),
                    "part_number": fan_module.get("part-number", "NA"),
                    "last_updated": int(time.time()),
                    "specifics": [self.get_fan_specfics(fan) for fan in fan_module['fan']]
                }
                data.append(fan_module_resp)
                logger.debug(self.log.svc_log(
                    f"Fan Manifest Data:{data}"))
        return data

    @staticmethod
    def get_expander_data(expander):
        """Returns expander data in specific format."""
        return {
            "uid": expander.get("durable-id", "NA"),
            "type": expander.get("type", "NA"),
            "description": expander.get("description", "NA"),
            "product": expander.get("object-name", "NA"),
            "manufacturer": expander.get("vendor", "NA"),
            "serial_number": expander.get("serial-number", "NA"),
            "version": expander.get("hardware-version", "NA"),
            "part_number": expander.get("part-number", "NA"),
            "specifics": [{
                "name": expander.get("name", "NA"),
                "location": expander.get("location", "NA"),
                "drawer_id": expander.get("drawer-id", "NA"),
                "status": expander.get("status", "NA"),
                "fw-revision": expander.get("fw-revision", "NA"),
            }]
        }

    def get_sideplane_expander_info(self):
        """Update and return sideplane information in specific format."""
        sideplane_expander_list = []
        data = []
        enclosures = ENCL.get_realstor_encl_data("enclosures")
        #TODO : Handle CORVAULT sideplane expander data without expecting drawers
        encl_drawers = enclosures[0].get("drawers") if enclosures else []
        if encl_drawers:
            for drawer in encl_drawers:
                sideplanes = drawer.get("sideplanes")
                sideplane_expander_list.extend(sideplanes)
        for sideplane in sideplane_expander_list:
            sideplane_dict = {
                "uid": sideplane.get("durable-id", "NA"),
                "type": sideplane.get("type", "NA"),
                "description": sideplane.get("description", "NA"),
                "product": sideplane.get("object-name", "NA"),
                "manufacturer": sideplane.get("vendor", "NA"),
                "serial_number": sideplane.get("serial-number", "NA"),
                "version": sideplane.get("hardware-version", "NA"),
                "part_number": sideplane.get("part-number", "NA"),
                "last_updated": int(time.time()),
                "specifics": [{
                    "name": sideplane.get("name", "NA"),
                    "location": sideplane.get("location", "NA"),
                    "drawer_id": sideplane.get("drawer-id", "NA"),
                    "status": sideplane.get("status", "NA"),
                    "expanders": [self.get_expander_data(expander) \
                        for expander in sideplane['expanders']]
                }]
            }
            data.append(sideplane_dict)
            logger.debug(self.log.svc_log(
                f"Sideplane Manifest Data:{data}"))
        return data

    def get_versions_info(self):
        """Update and return versions information in specific format."""
        data = []
        versions = ENCL.get_realstor_encl_data("versions")
        for version in versions:
            version_dict = {
                "uid": version.get("object-name", "NA"),
                "type": version.get("sc-cpu-type", "NA"),
                "description": version.get("description", "NA"),
                "product": version.get("object-name", "NA"),
                "manufacturer": version.get("vendor", "NA"),
                "serial_number": version.get("serial-number", "NA"),
                "version": version.get("bundle-version", "NA"),
                "part_number": version.get("part-number", "NA"),
                "last_updated": int(time.time()),
                "specifics": [{
                    "sc_cpu_type": version.get("sc-cpu-type", "NA"),
                    "bundle_version": version.get("bundle-version", "NA"),
                    "bundle_base_version": version.get("bundle-base-version", "NA"),
                    "build_date": version.get("build-date", "NA"),
                    "sc_fw": version.get("sc-fw", "NA"),
                    "sc_baselevel": version.get("sc-baselevel", "NA"),
                    "sc_memory": version.get("sc-memory", "NA"),
                    "sc_fu_version": version.get("sc-fu-version", "NA"),
                    "sc_loader": version.get("sc-loader", "NA"),
                    "capi_version": version.get("capi-version", "NA"),
                    "mc_fw": version.get("mc-fw", "NA"),
                    "mc_loader": version.get("mc-loader", "NA"),
                    "mc_base_fw": version.get("mc-base-fw", "NA"),
                    "fw_default_platform_brand": version.get("fw-default-platform-brand", "NA"),
                    "ec_fw": version.get("ec-fw", "NA"),
                    "pld_rev": version.get("pld-rev", "NA"),
                    "prm_version": version.get("prm-version", "NA"),
                    "hw_rev": version.get("hw-rev", "NA"),
                    "him_rev": version.get("him-rev", "NA"),
                    "him_model": version.get("him-model", "NA"),
                    "backplane_type": version.get("backplane-type", "NA"),
                    "host_channel_revision": version.get("host-channel_revision", "NA"),
                    "disk_channel_revision": version.get("disk-channel_revision", "NA"),
                    "mrc_version": version.get("mrc-version", "NA"),
                    "ctk_version": version.get("ctk-version", "NA")
                }]
            }
            data.append(version_dict)
            logger.debug(self.log.svc_log(
                f"Controller firmware Manifest Data:{data}"))
        return data
