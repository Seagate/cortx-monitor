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

import errno
import time
import json
import os

from cortx.utils.process import SimpleProcess
from cortx.utils.kv_store import KvStoreFactory
from cortx.utils.discovery.error import ResourceMapError
from framework.utils.conf_utils import GLOBAL_CONF, Conf, NODE_TYPE_KEY
from framework.base.sspl_constants import (MANIFEST_SVC_NAME, LSHW_FILE,
    MANIFEST_OUTPUT_FILE, HEALTH_UNDESIRED_VALS)
from framework.utils.service_logging import CustomLog, logger
from framework.utils.mon_utils import MonUtils
from framework.platforms.server.software import Service
from framework.platforms.server.platform import Platform
from server.server_resource_map import ServerResourceMap


class ServerManifest():
    """
    ServerManifest class provides resource map and related information
    like health.
    """

    name = "server_manifest"

    def __init__(self):
        """Initialize server manifest."""
        super().__init__()
        self.log = CustomLog(MANIFEST_SVC_NAME)
        server_type = Conf.get(GLOBAL_CONF, NODE_TYPE_KEY)
        # import pdb; pdb.set_trace()
        Platform.validate_server_type_support(self.log, ResourceMapError, server_type)
        self.field_mapping = {
            'id': 'uid',
            'class': 'type',
            'description': 'description',
            'product': 'product',
            'serial': 'serial_number',
            'vendor': 'manufacturer',
            'part_number': 'part_number',
            'model_number': 'model_number',
            'physid': 'physical_id',
            'version': 'version',
            'logicalname': 'logical_name'
        }
        self.class_mapping = {
            'memory': 'hw>memory[%s]>%s',
            'disk': 'hw>disk[%s]>%s',
            'storage': 'hw>storage[%s]>%s',
            'system': 'hw>system[%s]>%s',
            'processor': 'hw>cpu[%s]>%s',
            'network': 'hw>nw_port[%s]>%s',
            'power': 'hw>psu[%s]>%s',
            'volume': 'hw>volume[%s]>%s',
            'bus': 'hw>bus[%s]>%s',
            'bridge': 'hw>bridge[%s]>%s',
            'display': 'hw>display[%s]>%s',
            'input': 'hw>input[%s]>%s',
            'generic': 'hw>generic[%s]>%s'
        }
        self.kv_dict = {}
        sw_resources = {
            'os': self.get_os_server_info,
            'cortx_sw_services': self.get_cortx_service_info,
            'external_sw_services': self.get_external_service_info
        }
        fw_resources = {
            'bmc': self.get_bmc_version_info
        }
        # Extracting resource type for 'self.class_mapping' dictionary values
        # and adding to hw_resources for function mapping.
        hw_resources = {value[len('hw>'):-len('[%s]>%s')]: \
            self.get_hw_resources_info for value in self.class_mapping.values()}
        self.server_resources = {
            "hw": hw_resources,
            "sw": sw_resources,
            "fw": fw_resources
        }
        self.service = Service()
        self.platform = Platform()
        self.resource_indexing_map = ServerResourceMap.resource_indexing_map\
            ["manifest"]

    def get_data(self, rpath):
        """Fetch manifest information for given rpath."""
        logger.info(self.log.svc_log(
            f"Get Manifest data for rpath:{rpath}"))
        info = {}
        resource_found = False
        nodes = rpath.strip().split(">")
        leaf_node, _ = ServerResourceMap.get_node_info(nodes[-1])

        # Fetch manifest information for all sub nodes
        if leaf_node == "server":
            # Example rpath: 'node>server[0]'
            server_hw_data = self.get_server_hw_info()
            info = self.get_server_info(server_hw_data)
            resource_found = True
        elif leaf_node == "hw":
            # Example rpath: 'node>server[0]>hw'
            server_hw_data = self.get_server_hw_info()
            info = self.get_hw_resources_info(server_hw_data, "hw")["hw"]
            resource_found = True
        elif leaf_node in ["sw", "fw"]:
            # Example rpath: 'node>server[0]>fw' or sw
            for resource, method in self.server_resources[leaf_node].items():
                try:
                    info.update({resource: method()})
                    resource_found = True
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}: {err}"))
                    info = None
        else:
            # Example rpath: 'node>server[0]>hw>disk'
            server_hw_data = self.get_server_hw_info()
            for node in nodes:
                resource, _ = ServerResourceMap.get_node_info(node)
                for res_type in self.server_resources:
                    method = self.server_resources[res_type].get(resource)
                    if not method:
                        logger.error(
                            self.log.svc_log(
                                f"No mapping function found for {res_type}"))
                        continue
                    try:
                        if res_type == "hw":
                            info = method(server_hw_data, resource)
                        else:
                            info = method()
                        resource_found = True
                    except Exception as err:
                        logger.error(
                            self.log.svc_log(f"{err.__class__.__name__}: {err}"))
                        info = None
                if resource_found:
                    break

        if not resource_found:
            msg = f"Invalid rpath or manifest provider doesn't have support for'{rpath}'."
            logger.error(self.log.svc_log(f"{msg}"))
            raise ResourceMapError(errno.EINVAL, msg)

        info = MonUtils.normalize_kv(info, HEALTH_UNDESIRED_VALS, "Not Available")
        return info

    def get_server_info(self, server_hw_data):
        """Get server manifest information."""
        server = []
        info = {}
        for res_type in self.server_resources:
            info.update({res_type: {}})
            for fru, method in self.server_resources[res_type].items():
                try:
                    if res_type == "hw":
                        info[res_type].update({fru: method(server_hw_data, fru)})
                    else:
                        info[res_type].update({fru: method()})
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}:{err}"))
                    info[res_type].update({fru: []})
        info["last_updated"] = int(time.time())
        server.append(info)
        return server

    def get_server_hw_info(self):
        """Get server hw information."""
        cls_res_cnt = {}
        lshw_data = {}
        data, output_file = self.set_lshw_input_data()
        for kv_key in data.get_keys():
            if kv_key.endswith('class'):
                r_spec = data.get(kv_key)
                if r_spec in cls_res_cnt:
                    cls_res_cnt[r_spec] += 1
                else:
                    cls_res_cnt[r_spec] = 0
                if r_spec in self.class_mapping.keys():
                    for field in self.field_mapping.keys():
                        manifest_key = self.class_mapping[r_spec] % (cls_res_cnt[r_spec],
                            self.field_mapping[field])
                        self.map_manifest_server_data(field, manifest_key, data, kv_key)
        # Adding data to kv
        output_file.set(self.kv_dict.keys(), self.kv_dict.values())
        lshw_data = self.get_manifest_output_data()
        # Removing out storage enclosure (RBOD/JBOD) drives from disk server data
        # as they are coming from lshw , as those need to be represented
        # separately & uniquely
        if "disk" in lshw_data["hw"]:
            lshw_data["hw"]["disk"] = self.get_local_disk(lshw_data["hw"]["disk"])
        # Sort list by serial_number
        eth_ctrl = []
        for resource, sort_key_path in self.resource_indexing_map["hw"].items():
            if resource in lshw_data["hw"]:
                if resource == "nw_port":
                    # Separating out ethernet controller and ethernet interface
                    # data for sorting.
                    eth_ctrl = [eth_ctr for eth_ctr in lshw_data["hw"][resource] \
                        if eth_ctr['logical_name']=='NA']
                    lshw_data["hw"][resource] = [eth_interface for eth_interface \
                        in lshw_data["hw"][resource] if eth_interface[
                            'logical_name']!='NA']
                sorted_data = MonUtils.sort_by_specific_kv(
                    lshw_data["hw"][resource], sort_key_path, self.log)
                lshw_data["hw"][resource] = sorted_data
            if resource == "nw_port" and eth_ctrl:
                lshw_data["hw"][resource] += eth_ctrl
        return lshw_data

    def get_hw_resources_info(self, server_hw_data, resource=False):
        """Get server hw resource information."""
        server = {}
        if resource == "hw" and "hw" in server_hw_data:
            server.update({"hw": {}})
            # Sorting output dictionary according to data priority.
            for server_type in self.server_resources["hw"].keys():
                if server_type in server_hw_data["hw"]:
                    server["hw"][server_type] = server_hw_data["hw"][server_type]
        else:
            server = server_hw_data["hw"].get(resource, [])
        return server

    def set_lshw_input_data(self):
        """
        KvStoreFactory can not accept a dictionary as direct input and output
        It will support only JSON, YAML, TOML, INI, PROPERTIES files. So here
        we are fetching the lshw data and adding that to a file for further
        execution.
        """
        input_file = None
        output_file = None
        response, err, returncode = SimpleProcess("lshw -json").run()
        if returncode:
            msg = f"Failed to capture Node support data. Error:{str(err)}"
            logger.error(self.log.svc_log(msg))
            raise ResourceMapError(errno.EINVAL, msg)
        try:
            with open(LSHW_FILE, 'w+') as fp:
                json.dump(json.loads(response.decode("utf-8")), fp,  indent=4)
            with open(MANIFEST_OUTPUT_FILE, 'w+') as fp:
                json.dump({}, fp,  indent=4)
            input_file = KvStoreFactory.get_instance(f'json://{LSHW_FILE}').load()
            output_file = KvStoreFactory.get_instance(f'json://{MANIFEST_OUTPUT_FILE}')
        except Exception as e:
            msg = "Error in getting {0} file: {1}".format(LSHW_FILE, e)
            logger.error(self.log.svc_log(msg))
            raise ResourceMapError(errno.EINVAL, msg)
        return input_file, output_file

    def map_manifest_server_data(self, field, manifest_key, data, kv_key):
        """Mapping actual lshw output data with standard structured manifest data."""
        parent_id = ""
        base_key = '>'.join(kv_key.split('>')[:-1])
        if base_key:
            value = data.get(base_key+'>'+field)
        else:
            value = data.get(field)
        if isinstance(value, list):
            value = ','.join(value)
        value = value.replace(" (To be filled by O.E.M.)", "") \
            if value else 'NA'
        if field == 'id' and '>' in kv_key:
            parent_key = '>'.join(kv_key.split('>')[:-2])
            field = '>'+field if parent_key else field
            parent_id = data.get(parent_key+field)+"-"
        self.kv_dict[manifest_key] = parent_id + value

    def get_manifest_output_data(self):
        """Returns JSON data in the manifest output file."""
        data = {}
        try:
            with open(MANIFEST_OUTPUT_FILE) as json_file:
                data = json.loads(json_file.read())
        except Exception as e:
            msg = "Error in getting {0} file: {1}".format(MANIFEST_OUTPUT_FILE, e)
            logger.error(self.log.svc_log(msg))
            raise ResourceMapError(errno.EINVAL, msg)
        try:
            if os.path.exists(LSHW_FILE):
                os.remove(LSHW_FILE)
            if os.path.exists(MANIFEST_OUTPUT_FILE):
                os.remove(MANIFEST_OUTPUT_FILE)
        except OSError as ex:
            msg = f"Failed in manifest tmp files cleanup. Error:{str(ex)}"
            logger.warn(self.log.svc_log(msg))
        return data

    def get_cortx_service_info(self):
        """Get cortx service info in required format."""
        cortx_services = self.service.get_cortx_service_list()
        cortx_service_info = self.get_service_info(cortx_services)
        sort_key_path = self.resource_indexing_map["sw"]["cortx_sw_services"]
        cortx_service_info = MonUtils.sort_by_specific_kv(
            cortx_service_info, sort_key_path, self.log)
        return cortx_service_info

    def get_external_service_info(self):
        """Get external service info in required format."""
        external_services = self.service.get_external_service_list()
        external_service_info = self.get_service_info(external_services)
        sort_key_path = self.resource_indexing_map["sw"]["external_sw_services"]
        external_service_info = MonUtils.sort_by_specific_kv(
            external_service_info, sort_key_path, self.log)
        return external_service_info

    def get_service_info(self, services):
        """Returns node server services info."""
        services_info = []
        for service in services:
            response = self.service.get_systemd_service_info(self.log, service)
            if response is not None:
                uid, _, health_description, _, specifics = response
                service_info = {
                    "uid": uid,
                    "type": "software",
                    "description": health_description,
                    "product": specifics[0].pop("service_name"),
                    "manufacturer": "Not Applicable",
                    "serial_number": "Not Applicable",
                    "part_number": "Not Applicable",
                    "version": specifics[0].pop("version"),
                    "last_updated": int(time.time()),
                    "specifics": specifics
                }
                services_info.append(service_info)
        return services_info

    def get_bmc_version_info(self):
        """Returns node server bmc info."""
        bmc_data = []
        specifics = self.platform.get_bmc_info()
        if specifics:
            bmc = {
                "uid": 'bmc',
                "type": "firmware",
                "description": "BMC and IPMI version information",
                "product": specifics.get("product_name", "NA"),
                "manufacturer": specifics.get("manufacturer_name", "NA"),
                "serial_number": "Not Applicable",
                "part_number": "Not Applicable",
                "version": specifics.get("firmware_revision", "NA"),
                "last_updated": int(time.time()),
                "specifics": [specifics]
            }
            bmc_data.append(bmc)
        return bmc_data

    def get_os_server_info(self):
        """Returns node server os info."""
        os_data = []
        specifics = self.platform.get_os_info()
        if specifics:
            os_info = {
                "uid": specifics.get("id", "NA"),
                "type": "software",
                "description": "OS information",
                "product": specifics.get("pretty_name", "NA"),
                "manufacturer": specifics.get("manufacturer_name",
                                    "Not Applicable"),
                "serial_number": "Not Applicable",
                "part_number": "Not Applicable",
                "version": specifics.get("version", "NA"),
                "last_updated": int(time.time()),
                "specifics": [specifics]
            }
            os_data.append(os_info)
        return os_data

    @staticmethod
    def get_local_disk(disks):
        #TODO: We need better logic to identify server local disks.
        local_disk = []
        for disk in disks:
            if disk.get("version") in ["G265", "G280"]:
                continue
            else:
                local_disk.append(disk)
        return local_disk
