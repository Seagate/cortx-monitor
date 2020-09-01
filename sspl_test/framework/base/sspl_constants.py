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

from enum import Enum

PRODUCT_NAME = 'LDR_R1'
PRODUCT_FAMILY = 'cortx'
enabled_products = [ "CS-A", "SINGLE","DUAL","CLUSTER" ,"LDR_R1", "LDR_R2"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]
RESOURCE_PATH = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/resources/"

SSPL_STORE_TYPE = 'consul'
CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'
CONSUL_PATH = f"/opt/seagate/{PRODUCT_FAMILY}/hare/bin"

# required only for init
component = 'sspl_test/config'
file_store_config_path = f'/opt/seagate/{PRODUCT_FAMILY}/sspl/sspl_test/conf/sspl_tests.conf'
salt_provisioner_pillar_sls = 'sspl'

class AlertTypes(Enum):
    GET = "get"


class SensorTypes(Enum):
    TEMPERATURE = "temperature"
    CURRENT = "current"
    VOLTAGE = "voltage"


class SeverityTypes(Enum):
    INFORMATIONAL = "informational"


class ResourceTypes(Enum):
    SENSOR = "sensor"
    INTERFACE = "interface"


class EnclInterface(Enum):
    SAS = "SAS"


class StoreTypes(Enum):
    FILE = "file"
    CONSUL = "consul"


if __name__ == "__main__":
    print(' '.join(enabled_products))

# Consul paths for enclosure connection
GET_USERNAME = "/opt/seagate/cortx/hare/bin/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/user"
GET_PASSWD = "/opt/seagate/cortx/hare/bin/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/secret"
GET_PRIMARY_IP = "/opt/seagate/cortx/hare/bin/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/ip"
GET_PRIMARY_PORT = "/opt/seagate/cortx/hare/bin/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/primary_mc/port"
GET_SECONDARY_IP = "/opt/seagate/cortx/hare/bin/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/secondary_mc/ip"
GET_SECONDARY_PORT = "/opt/seagate/cortx/hare/bin/consul kv get sspl/config/STORAGE_ENCLOSURE/controller/secondary_mc/port"
GET_CLUSTER_ID = "/opt/seagate/cortx/hare/bin/consul kv get sspl/config/SYSTEM_INFORMATION/cluster_id"

SSPL_TEST_PATH = "/opt/seagate/cortx/sspl/sspl_test"
