#!/usr/bin/python3.6

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

from cortx.utils.conf_store import Conf
from framework.utils.conf_utils import (GLOBAL_CONF, SSPL_CONF,
            CLUSTER, SERVER_NODES, MACHINE_ID, STORAGE, STORAGE_SET_ID,
            ENCLOSURE_ID, CONTROLLER, PRIMARY, IP, PORT, SECONDARY,
            USER, PRODUCT, RSYSLOG, HOST, NODE_TYPE, TYPE, RELEASE,
            TARGET_BUILD, SECRET, CONF_API_DELIMITER)
from framework.base.sspl_constants import (DATACENTER01, RACK01, SERVERNODE01,
                CLUSTER01, DEFAULT_MC_IP, DEFAULT_SYSLOG_HOST, DEFAULT_SYSLOG_PORT)


class GlobalConf:
    """Base Class to fetch global config values."""

    Conf.load(SSPL_CONF, "yaml:///etc/sspl.conf")
    global_config = Conf.get(SSPL_CONF, "SYSTEM_INFORMATION>global_config_copy_url")
    Conf.load(GLOBAL_CONF, global_config)
    
    def __init__(self):
        self.initialize()
        self.map_global_config_key_values()

    def initialize(self):
        self.SRVNODE = Conf.get(GLOBAL_CONF, f'{CLUSTER}>{SERVER_NODES}')[MACHINE_ID]
        self.ENCLOSURE = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{self.SRVNODE}>{STORAGE}>{ENCLOSURE_ID}")

    def fetch_global_config(self, config_list):
        response = {}
        default_val = ''
        req_fields = []
        for key in config_list:
            if key not in self.global_conf_dict.keys():
                return
            output = self.global_conf_dict[key]
            for ele in output:
                if "default:" in ele:
                    default_val = ele.split(':')[1]
                else:
                    req_fields.append(ele)
            req_string =  CONF_API_DELIMITER.join(req_fields)
            global_val = Conf.get(GLOBAL_CONF, req_string, default_val)
            response[key] = global_val
            req_fields = []
        return response

    def fetch_sspl_config(self, query_string=False, default_val=""):
        try:
            if not query_string:
                return
            response = Conf.get(SSPL_CONF, query_string, default_val)
            return response
        except Exception as ex:
            print("Failed to fetch the sspl config:{}".format(str(ex)))

    def set_sspl_config(self, request="", value=False):
        try:
            if not value:
                return
            response = Conf.set(SSPL_CONF, request, value)
            return response
        except Exception as ex:
            print("Failed to set the sspl config:{}".format(str(ex)))

    def map_global_config_key_values(self):
        self.global_conf_dict = {
            "cluster_id": [CLUSTER, 'cluster_id', 'default:' + CLUSTER01],
            "site_id": [CLUSTER, self.SRVNODE, 'site_id', 'default:' + DATACENTER01],
            "node_id": [CLUSTER, self.SRVNODE, 'node_id', 'default:' + SERVERNODE01],
            "rack_id": [CLUSTER, self.SRVNODE, 'rack_id', 'default:'+ RACK01],
            "mc1": [STORAGE, self.ENCLOSURE, CONTROLLER, PRIMARY, IP, 'default:'+ DEFAULT_MC_IP],
            "mc1_wsport": [STORAGE, self.ENCLOSURE, CONTROLLER, PRIMARY, PORT],
            "mc2": [STORAGE, self.ENCLOSURE, CONTROLLER, SECONDARY, IP, 'default:'+ DEFAULT_MC_IP],
            "mc2_wsport": [STORAGE, self.ENCLOSURE, CONTROLLER, SECONDARY, PORT],
            "user": [STORAGE, self.ENCLOSURE, CONTROLLER, USER],
            "secret": [STORAGE, self.ENCLOSURE, CONTROLLER, SECRET],
            "storage_type": [STORAGE, self.ENCLOSURE, TYPE, 'default:virtual'],
            "storage_set_id": [CLUSTER, self.SRVNODE, STORAGE_SET_ID, 'default:ST01'],
            "server_type": [CLUSTER, self.SRVNODE, NODE_TYPE, 'default:virtual'],
            "target_build": [RELEASE, TARGET_BUILD, 'default:NA'],
            "setup": [RELEASE, 'setup', 'default:ssu'],
            "product": [RELEASE, PRODUCT],
            "bmc_user": [CLUSTER, self.SRVNODE, 'BMC', USER, 'default:ADMIN'],
            "bmc_secret": [CLUSTER, self.SRVNODE, 'BMC', SECRET, 'default:ADMIN'],
            "bmc_ip": [CLUSTER, self.SRVNODE, 'BMC', IP],
            "rsyslog_host": [RSYSLOG, HOST, 'default:'+ DEFAULT_SYSLOG_HOST],
            "rsyslog_port": [RSYSLOG, PORT, 'default:'+ str(DEFAULT_SYSLOG_PORT)]
        }

