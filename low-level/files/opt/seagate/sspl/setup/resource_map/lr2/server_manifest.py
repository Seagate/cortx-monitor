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
from framework.utils.conf_utils import GLOBAL_CONF, Conf, NODE_TYPE_KEY
from error import ManifestError
from resource_map import CortxManifest
from framework.base.sspl_constants import (MANIFEST_SVC_NAME, LSHW_FILE,
    MANIFEST_OUTPUT_FILE)
from framework.utils.service_logging import CustomLog, logger
from framework.utils.utility import Utility
from framework.platforms.server.software import Service
from framework.platforms.server.platform import Platform


class ServerManifest(CortxManifest):
    """ServerManifest class provides resource map and related information
    like health.
    """

    name = "server_manifest"

    def __init__(self):
        """Initialize server manifest."""
        super().__init__()
        self.log = CustomLog(MANIFEST_SVC_NAME)
        server_type = Conf.get(GLOBAL_CONF, NODE_TYPE_KEY)
        Utility.validate_server_type_support(self.log, ManifestError, server_type)
        self.field_mapping = {
            'id': 'uid',
            'class': 'type',
            'description': 'description',
            'product': 'product',
            'serial': 'serial_number',
            'vendor': 'manufacturer',
            'part_number': 'part_number',
            'model_number': 'model_number',
            'physid': 'physid',
            'version': 'version'
        }
        self.class_mapping = {
            'memory': 'hw>memory[%s]>%s',
            'disk': 'hw>disk[%s]>%s',
            'storage': 'hw>storage[%s]>%s',
            'system': 'hw>system[%s]>%s',
            'processor': 'hw>processor[%s]>%s',
            'network': 'hw>network[%s]>%s',
            'power': 'hw>power[%s]>%s',
            'volume': 'hw>volumes[%s]>%s',
            'bus': 'hw>bus[%s]>%s',
            'bridge': 'hw>bridge[%s]>%s',
            'display': 'hw>display[%s]>%s',
            'generic': 'hw>generic[%s]>%s',
            'input': 'hw>input[%s]>%s'
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
        self.server_resources = {
            "fw": fw_resources,
            "sw": sw_resources,
            "hw": self.get_server_lshw_info
        }
        self.service = Service()
        self.platform = Platform()

    def get_manifest_info(self, rpath):
        """
        Fetch manifest information for given rpath.
        """
        logger.info(self.log.svc_log(
            f"Get Manifest data for rpath:{rpath}"))
        info = {}
        resource_found = False
        nodes = rpath.strip().split(">")
        leaf_node, _ = Utility.get_node_details(nodes[-1])

        # Fetch health information for all sub nodes
        if leaf_node == "compute":
            info = self.get_server_manifest_info()
            resource_found = True
        elif leaf_node == "hw":
            info = self.get_server_lshw_info()
            resource_found = True
        elif leaf_node == "sw":
            for resource, method in self.server_resources[leaf_node].items():
                try:
                    info.update({resource: method()})
                    resource_found = True
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}: {err}"))
                    info = None
        else:
            for node in nodes:
                resource, _ = Utility.get_node_details(node)
                for res_type in self.server_resources:
                    if res_type == "hw":
                        method = self.server_resources.get(resource)
                    else:
                        method = self.server_resources[res_type].get(resource)
                    if not method:
                        logger.error(
                            self.log.svc_log(
                                f"No mapping function found for {res_type}"))
                        continue
                    try:
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
            raise ManifestError(errno.EINVAL, msg)

        return info

    def get_server_manifest_info(self):
        """Get server manifest information."""
        server = []
        info = {}
        for res_type in self.server_resources:
            info.update({res_type: {}})
            if res_type == "hw":
                try:
                    info[res_type].update(self.server_resources[res_type]()["hw"])
                except Exception as err:
                    logger.error(
                        self.log.svc_log(f"{err.__class__.__name__}:{err}"))
                    info[res_type].update({})
            else:
                for fru, method in self.server_resources[res_type].items():
                    try:
                        info[res_type].update({fru: method()})
                    except Exception as err:
                        logger.error(
                            self.log.svc_log(f"{err.__class__.__name__}:{err}"))
                        info[res_type].update({fru: []})
        info["last_updated"] = int(time.time())
        server.append(info)
        return server
    
    def get_server_lshw_info(self):
        """Get server manifest information."""
        cls_res_cnt = {}
        server = {"hw":{}}
        data, kvs_dst = self.set_lshw_input_data()
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
        kvs_dst.set(self.kv_dict.keys(), self.kv_dict.values())
        server_unsorted = self.get_manifest_output_data()
        # Sorting dictionary according to priority.
        for server_type in self.class_mapping.keys():
            if server_type in server_unsorted["hw"]:
                server["hw"][server_type] = server_unsorted["hw"][server_type]
        return server

    def set_lshw_input_data(self):
        """Fetch lshw data and update it into a file for further execution."""
        kvs_src = None
        kvs_dst = None
        response, err, returncode = SimpleProcess("lshw -json").run()
        if returncode:
            msg = f"Failed to capture Node support data. Error:{str(err)}"
            logger.error(self.log.svc_log(msg))
            raise ManifestError(errno.EINVAL, msg)
        try:
            with open(LSHW_FILE, 'w+') as fp:
                json.dump(json.loads(response.decode("utf-8")), fp,  indent=4)
            with open(MANIFEST_OUTPUT_FILE, 'w+') as fp:
                json.dump({}, fp,  indent=4)
            kvs_src = KvStoreFactory.get_instance(f'json://{LSHW_FILE}').load()
            kvs_dst = KvStoreFactory.get_instance(f'json://{MANIFEST_OUTPUT_FILE}')
        except Exception as e:
            msg = "Error in getting {0} file: {1}".format(LSHW_FILE, e)
            logger.error(self.log.svc_log(msg))
            raise ManifestError(errno.EINVAL, msg)
        return kvs_src, kvs_dst

    def map_manifest_server_data(self, field, manifest_key, data, kv_key):
        parent_id = ""
        base_key = '>'.join(kv_key.split('>')[:-1])
        if base_key:
            value = data.get(base_key+'>'+field)
        else:
            value = data.get(field)
        value = value.replace(" (To be filled by O.E.M.)", "") \
            if value else 'NA'
        if field == 'id' and '>' in kv_key:
            parent_key = '>'.join(kv_key.split('>')[:-2])
            field = '>'+field if parent_key else field
            parent_id = data.get(parent_key+field)+"-"
        self.kv_dict[manifest_key] = parent_id + value
    
    def get_manifest_output_data(self):
        data = {}
        try:
            with open(MANIFEST_OUTPUT_FILE) as json_file:
                data = json.loads(json_file.read())
        except Exception as e:
            msg = "Error in getting {0} file: {1}".format(json_file, e)
            logger.error(self.log.svc_log(msg))
            raise ManifestError(errno.EINVAL, msg)
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
        return cortx_service_info

    def get_external_service_info(self):
        """Get external service info in required format."""
        external_services = self.service.get_external_service_list()
        external_service_info = self.get_service_info(external_services)
        return external_service_info

    def get_service_info(self, services):
        services_info = []
        for service in services:
            response = self.service.get_systemd_service_info(self.log, service)
            if response is not None:
                uid, _, health_description, _, specifics = response
                service_info = {
                    "uid": uid,
                    "type": "NA",
                    "description": health_description,
                    "product": specifics[0].pop("service_name"),
                    "manufacturer": "NA",
                    "serial_number": "NA",
                    "part_number": "NA",
                    "version": specifics[0].pop("version"),
                    "last_updated": int(time.time()),
                    "specifics": specifics
                }
                services_info.append(service_info)
        return services_info

    def get_bmc_version_info(self):
        bmc_data = []
        specifics = {}
        cmd = "bmc info"
        out, _, retcode = self.platform._ipmi._run_ipmitool_subcommand(cmd)
        if retcode == 0:
            out_lst = out.split("\n")
            for line in out_lst:
                data = line.split(':')
                if len(data)>1 and data[1].strip() != "":
                    key = data[0].strip().lower().replace(" ","_")
                    value = data[1].strip()
                    specifics.update({key: value})
            bmc = {
                "uid": 'bmc',
                "type": "NA",
                "description": "BMC and IPMI version information",
                "product": specifics.get("product_name", "NA"),
                "manufacturer": specifics.get("manufacturer_name", "NA"),
                "serial_number": "NA",
                "part_number": "NA",
                "version": specifics.get("firmware_revision", "NA"),
                "last_updated": int(time.time()),
                "specifics": [specifics]
            }
            bmc_data.append(bmc)
        return bmc_data
    
    def get_os_server_info(self):
        os_data = []
        specifics = self.platform.get_os_info()
        if specifics:
            os_info = {
                "uid": specifics.get("id", "NA"),
                "type": "os",
                "description": "OS information",
                "product": specifics.get("pretty_name", "NA"),
                "manufacturer": specifics.get("manufacturer_name", "NA"),
                "serial_number": "NA",
                "part_number": "NA",
                "version": specifics.get("version", "NA"),
                "last_updated": int(time.time()),
                "specifics": [specifics]
            }
            os_data.append(os_info)
        return os_data
