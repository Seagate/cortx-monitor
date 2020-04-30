#!/usr/bin/python3.6
from enum import Enum

enabled_products = ["EES", "CS-A"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]
setups = ["eos"]
RESOURCE_PATH = "/opt/seagate/eos/sspl/resources/"
CLI_RESOURCE_PATH = "/opt/seagate/eos/sspl/cli"
DATA_PATH = "/var/eos/sspl/data/"
NODE_ID = "001"
SITE_ID = "001"
RACK_ID = "001"
SSPL_STORE_TYPE = 'consul'
CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'
SYSLOG_HOST = 'localhost'
SYSLOG_PORT = '514'
SYSINFO = "SYSTEM_INFORMATION"
PRODUCT = "product"
SETUP = "setup"

# TODO : need to fetch node_key using salt python API.
# Facing issue of service is going in loop till it eat's all the memory
import subprocess
subout = subprocess.Popen('salt-call grains.get id --output=newline_values_only', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
result = subout.stdout.readlines()
if result == [] or result == "":
    subout = subprocess.Popen('hostname', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = subout.stdout.readlines()
    if result == [] or result == "":
        print("CRITICAL: using node_id ('srvnode-1') as we are not able to fetch it from hostname command.")
        node_key_id = 'srvnode-1'
    else:
        if result[0].decode().rstrip('\n') in ['eosnode-1', 'srvnode-1']:
            node_key_id = 'srvnode-1'
        elif result[0].decode().rstrip('\n') in ['eosnode-2', 'srvnode-2']:
            node_key_id = 'srvnode-2'
        else:
            print("CRITICAL: using node_id ('srvnode-1') as hostname not able to match with required node name.")
            node_key_id = 'srvnode-1'
else:
    node_key_id = result[0].decode().rstrip('\n')


COMMON_CONFIGS = {
    "SYSTEM_INFORMATION": {
        "sspl_key" : "key_provided_by_provisioner",
        "operating_system" : "operating_system",
        "kernel_version" : "kernel_version",
        "product" : "product",
        "site_id" : "site_id",
        "rack_id" : "rack_id",
        "node_id" : f"{node_key_id}/node_id",
        "cluster_id" : "cluster_id",
        "syslog_host" : "syslog_host",
        "syslog_port" : "syslog_port",
        "setup" : "setup",
        "data_path" : "data_path"
    },
    "STORAGE_ENCLOSURE": {
        "sspl_key" : "key_provided_by_provisioner",
        "primary_controller_ip" : "controller/primary_mc/ip",
        "primary_controller_port" : "controller/primary_mc/port",
        "secondary_controller_ip" : "controller/secondary_mc/ip",
        "secondary_controller_port" : "controller/secondary_mc/port",
        "user" : "controller/user",
        "password" : "controller/secret",
        "mgmt_interface" : "controller/mgmt_interface"
    },
    "RABBITMQCLUSTER": {
        "sspl_key" : "key_provided_by_provisioner",
        "cluster_nodes" : "rabbitmq/cluster_nodes",
        "erlang_cookie" : "rabbitmq/erlang_cookie"
    }
}

SSPL_CONFIGS = ['log_level', 'cli_type', 'sspl_log_file_path', 'cluster_id', 'storage_enclosure', 'setup']

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
    RHEL7 = "Red Hat Enterprise Linux Server 7.7 (Maipo)"
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
