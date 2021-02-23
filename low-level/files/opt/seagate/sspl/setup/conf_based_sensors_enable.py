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

import os
import consul

from cortx.utils.conf_store import Conf
from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.error import SetupError
from cortx.sspl.bin.sspl_constants import (CONSUL_HOST,
                                           CONSUL_PORT,
                                           PRODUCT_FAMILY,
                                           SSPL_STORE_TYPE,
                                           GLOBAL_CONFIG_INDEX)

def update_sensor_info(config_index):

    key = 'monitor'

    sensors = dict()
    sensors["REALSTORSENSORS"] = "true"
    sensors["NODEHWSENSOR"] = "true"
    sensors["SYSTEMDWATCHDOG"] = "true"
    sensors["RAIDSENSOR"] = "true"
    sensors["SASPORTSENSOR"] = "true"
    sensors["MEMFAULTSENSOR"] = "true"
    sensors["CPUFAULTSENSOR"] = "true"

    try:
        with open("/etc/machine-id") as f:
            machine_id = f.read().strip("\n")
    except Exception as err:
        raise SetupError(1, "Failed to get machine-id. - %s" % (err))

    srvnode = Conf.get(GLOBAL_CONFIG_INDEX,
                       "cluster>server_nodes>%s" % (machine_id))
    enclosure_id = Conf.get(GLOBAL_CONFIG_INDEX,
                            "cluster>%s>storage>enclosure_id" % (srvnode))
    node_key_id = Conf.get(GLOBAL_CONFIG_INDEX,
                           'cluster>server_nodes>%s' % (machine_id))

    storage_type = Conf.get(GLOBAL_CONFIG_INDEX,
                            'storage>%s>type' % enclosure_id)
    if storage_type and storage_type.lower() in ["virtual", "jbod"]:
        sensors["REALSTORSENSORS"] = "false"

    server_type = Conf.get(GLOBAL_CONFIG_INDEX,
                           'cluster>%s>node_type' % (node_key_id))
    if server_type and server_type.lower() in ["virtual"]:
        sensors["NODEHWSENSOR"] = "false"
        sensors["SASPORTSENSOR"] = "false"
        sensors["MEMFAULTSENSOR"] = "false"
        sensors["CPUFAULTSENSOR"] = "false"
        sensors["RAIDSENSOR"] = "false"

    # Onward LDR_R2, consul will be abstracted out and it won't exit as hard dependeny of SSPL
    # Note: SSPL has backward compatibility to LDR_R1 and there consul is a dependency of SSPL.
    if SSPL_STORE_TYPE == "consul":
        host = os.getenv('CONSUL_HOST', CONSUL_HOST)
        port = os.getenv('CONSUL_PORT', CONSUL_PORT)
        try:
            consul_conn = consul.Consul(host=host, port=port)
            for sect, value in sensors.items():
                consul_conn.kv.put("sspl/config/%s/monitor" % sect, value)
        except Exception as cerror:
            print("Error in connecting with consul: {}".format(cerror))

    # Update sensor information in config
    for sect, value in sensors.items():
        Conf.set(config_index, '%s>%s' % (sect, key), value)

    Conf.save(config_index)
