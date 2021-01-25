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

from cortx.sspl.bin.sspl_constants import (CONSUL_HOST, CONSUL_PORT,
    PRODUCT_FAMILY, file_store_config_path, storage_type, server_type, SSPL_STORE_TYPE)


# TODO: Update sensor information in ConfStore
# from cortx.utils.conf_store import Conf

def update_sensor_info():
    Conf.load('sspl', file_store_config_path)

    key = 'monitor'

    sensors = dict()
    sensors["REALSTORSENSORS"] = "true"
    sensors["NODEHWSENSOR"] = "true"
    sensors["SYSTEMDWATCHDOG"] = "true"
    sensors["RAIDSENSOR"] = "true"
    sensors["SASPORTSENSOR"] = "true"
    sensors["MEMFAULTSENSOR"] = "true"
    sensors["CPUFAULTSENSOR"] = "true"

    if storage_type.lower() in ["virtual", "jbod"]:
        sensors["REALSTORSENSORS"] = "false"

    if server_type.lower() in ["virtual"]:
        sensors["NODEHWSENSOR"] = "false"
        sensors["SASPORTSENSOR"] = "false"
        sensors["MEMFAULTSENSOR"] = "false"
        sensors["CPUFAULTSENSOR"] = "false"
        sensors["RAIDSENSOR"] = "false"

    for sect, value in sensors.items():
        Conf.set('sspl', '%s>%s' % (sect, key), value)

    Conf.save('sspl')

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

    # Update sensor information for sspl_test
    test_file_config_path="/opt/seagate/%s/sspl/sspl_test/conf/sspl_tests.conf" % PRODUCT_FAMILY
    Conf.load('sspl_test', test_file_config_path)
    for sect, value in sensors.items():
        Conf.set('sspl_test', '%s>%s' % (sect, key), value)

    Conf.save('sspl_test')
