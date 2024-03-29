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

# TODO - Avoid duplicate code between sspl and sspl_test

from enum import Enum


PRODUCT_NAME = "LDR_R2"
PRODUCT_FAMILY = "cortx"
enabled_products = ["CS-A", "SINGLE", "DUAL", "CLUSTER", "LDR_R1", "LDR_R2"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]
RESOURCE_PATH = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/low-level/json_msgs/schemas/"
DATA_PATH = f"/var/{PRODUCT_FAMILY}/sspl/data/"
IEM_DATA_PATH = "/var/%s/sspl/data/iem/sspl_iems" % (PRODUCT_FAMILY)

SSPL_STORE_TYPE = "file"
CONSUL_HOST = "127.0.0.1"
CONSUL_PORT = "8500"
CONSUL_PATH = "/usr/bin/"
DEFAULT_NODE_ID = "SN01"

# required only for init
component = "sspl_test/config"
file_store_config_path = (
    f"/opt/seagate/{PRODUCT_FAMILY}/sspl/sspl_test/conf/sspl_tests.conf"
)
salt_provisioner_pillar_sls = "sspl"


class BMCInterface(Enum):
    BMC_IF_CACHE = f"{DATA_PATH}server/BMC_INTERFACE"
    ACTIVE_BMC_IF = f"{BMC_IF_CACHE}/ACTIVE_BMC_IF"


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


class ServiceTypes(Enum):
    MESSAGING = "messaging"


if __name__ == "__main__":
    print(" ".join(enabled_products))

SSPL_TEST_PATH = "/opt/seagate/cortx/sspl/sspl_test"
