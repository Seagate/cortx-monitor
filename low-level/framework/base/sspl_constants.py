#!/usr/bin/python3.6
from enum import Enum

enabled_products = ["EES", "CS-A"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]
setups = ["eos"]
RESOURCE_PATH = "/opt/seagate/eos/sspl/resources/"
CLI_RESOURCE_PATH = "/opt/seagate/eos/sspl/cli"
SSPL_STORE_TYPE = 'consul'
CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'
SYSINFO = "SYSTEM_INFORMATION"
PRODUCT = "product"
SETUP = "setup"

# required only for init
component = 'sspl/config'
file_store_config_path = '/etc/sspl.conf'
salt_provisioner_pillar_sls = 'sspl'
salt_uniq_attr_per_node = ['cluster_id']
salt_uniq_passwd_per_node = ['RABBITMQINGRESSPROCESSOR', 'RABBITMQEGRESSPROCESSOR', 'LOGGINGPROCESSOR']

class AlertTypes(Enum):
    GET = "get"
    FAULT = "fault"


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
    RABBITMQ = "rabbitmq"
    STORAGE_ENCLOSURE = "storage_enclosure"

class OperatingSystem(Enum):
    CENTOS7 = "centos7"
    CENTOS6 = "centos6"
    RHEL7 = "rhel7"
    RHEL6 = "rhel6"
    OSX = "osX"

iem_severity_types = {
    "A": "alert",
    "X": "critical",
    "E": "error",
    "W": "warning",
    "N": "notice",
    "C": "configuration",
    "I": "informational",
    "D": "detail",
    "B": "debug"
}

iem_severity_to_alert_mapping = {
    "A": AlertTypes.FAULT.value,
    "X": AlertTypes.FAULT.value,
    "E": AlertTypes.FAULT.value,
    "W": AlertTypes.GET.value,
    "N": AlertTypes.GET.value,
    "C": AlertTypes.GET.value,
    "I": AlertTypes.GET.value,
    "D": AlertTypes.GET.value,
    "B": AlertTypes.GET.value
}

iem_source_types = {
    "H": "Hardware",
    "S": "Software",
    "F": "Firmware",
    "O": "OS"
}

if __name__ == "__main__":
    print(' '.join(enabled_products))
