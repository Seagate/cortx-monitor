#!/usr/bin/python3.6
from enum import Enum

PRODUCT_NAME = 'ECS'
PRODUCT_FAMILY = 'cortx'
enabled_products = [ "CS-A", "SINGLE", "EES", "ECS"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]
RESOURCE_PATH = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/resources/"

SSPL_STORE_TYPE = 'consul'
CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'

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
