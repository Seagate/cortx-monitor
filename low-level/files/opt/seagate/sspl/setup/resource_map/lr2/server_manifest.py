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
import subprocess
import os

from framework.utils.conf_utils import GLOBAL_CONF, Conf, NODE_TYPE_KEY
from error import ManifestError
from resource_map import CortxManifest
from framework.base.sspl_constants import (MANIFEST_SVC_NAME, LSHW_FILE,
    MANIFEST_OUTPUT_FILE)
from framework.utils.service_logging import CustomLog, logger
from framework.utils.utility import Utility
from cortx.utils.kv_store import KvStoreFactory


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
            'disk': 'hw>disks[%s]>%s',
            'network': 'hw>networks[%s]>%s',
            'volume': 'hw>volumes[%s]>%s',
            'bus': 'hw>buses[%s]>%s',
            'memory': 'hw>memorys[%s]>%s',
            'processor': 'hw>processors[%s]>%s',
            'bridge': 'hw>bridges[%s]>%s',
            'generic': 'hw>generics[%s]>%s',
            'storage': 'hw>storages[%s]>%s',
            'input': 'hw>inputs[%s]>%s',
            'display': 'hw>displays[%s]>%s',
            'system': 'hw>systems[%s]>%s',
            'power': 'hw>powers[%s]>%s'
        }
        self.kv_dict = {}

    def get_manifest_info(self, rpath):
        """
        Fetch manifest information for given rpath.
        """
        logger.info(self.log.svc_log(
            f"Get Manifest data for rpath:{rpath}"))
        info = []
        resource_found = False

        # Fetch server manifest information from lshw
        if "compute" in rpath:
            info = self.get_server_manifest_info()
            resource_found = True

        if not resource_found:
            msg = f"Invalid rpath or manifest provider doesn't have support for'{rpath}'."
            logger.error(self.log.svc_log(msg))
            raise ManifestError(errno.EINVAL, msg)
        return info

    def get_server_manifest_info(self):
        """Get server manifest information."""
        server = []
        cls_res_cnt = {}
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
        server = self.get_manifest_output_data()
        return server
    
    def set_lshw_input_data(self):
        """Fetch lshw data and update it into a file for further execution."""
        kvs_src = None
        kvs_dst = None
        proc = subprocess.Popen(['lshw', '-json'], stdout=subprocess.PIPE)
        str_dict, err = proc.communicate()
        if err:
            msg = f"Failed to capture Node support data. Error:{str(err)}"
            logger.error(self.log.svc_log(msg))
            raise ManifestError(errno.EINVAL, msg)
        try:
            with open(LSHW_FILE, 'w+') as fp:
                json.dump(json.loads(str_dict.decode("utf-8")), fp,  indent=4)
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
        return [data]
