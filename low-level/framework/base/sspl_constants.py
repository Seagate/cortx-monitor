#!/usr/bin/python3.6
from enum import Enum

enabled_products = ["EES", "CS-A"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]
RESOURCE_PATH = "/opt/seagate/eos/sspl/resources/"
SSPL_STORE_TYPE = 'consul'
CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'

# required only for init
component = 'sspl'
file_store_config_path = '/etc/sspl.conf'
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

iem_source_types = {
    "H": "Hardware",
    "S": "Software",
    "F": "Firmware",
    "O": "OS"
}

def normalize_dict_keys(jsonMsg):
    """Normalize all keys coming from firmware from - to _"""
    new_dic = {}
    for k, v in jsonMsg.items():
        if isinstance(v, dict):
            v = normalize_dict_keys(v)
        elif isinstance(v, list):
            new_lst = []
            for d in v:
                d = normalize_dict_keys(d)
                new_lst.append(d)
            v = new_lst
        new_dic[k.replace('-', '_')] = v
    return new_dic

if __name__ == "__main__":
    print(' '.join(enabled_products))
