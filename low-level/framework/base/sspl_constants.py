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

import subprocess
import ast
import sys
import os
from enum import Enum

# using cortx package
from framework.utils.salt_util import SaltInterface
from framework.utils.service_logging import logger


PRODUCT_NAME = 'LR2'
PRODUCT_FAMILY = 'cortx'
USER = "sspl-ll"
enabled_products = ["CS-A", "SINGLE","DUAL", "CLUSTER", "LDR_R1", "LR2"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]
setups = ["vm", "cortx", "ssu", "gw", "cmu"]
RESOURCE_PATH = "/opt/seagate/%s/sspl/low-level/json_msgs/schemas/" % (PRODUCT_FAMILY)
CLI_RESOURCE_PATH = "/opt/seagate/%s/sspl/low-level/tests/manual" % (PRODUCT_FAMILY)
DATA_PATH = "/var/%s/sspl/data/" % (PRODUCT_FAMILY)
IEM_DATA_PATH = "/var/%s/sspl/data/iem/sspl_iem"  %(PRODUCT_FAMILY)
SSPL_CONFIGURED_DIR = "/var/%s/sspl/" % (PRODUCT_FAMILY)
SSPL_CONFIGURED = "%s/sspl-configured" % (SSPL_CONFIGURED_DIR)
RESOURCE_HEALTH_VIEW = "/usr/bin/resource_health_view"
CONSUL_DUMP = "/opt/seagate/%s/sspl/bin/consuldump.py" % (PRODUCT_FAMILY)
NODE_ID = "SN01"
SITE_ID = "DC01"
RACK_ID = "RC01"
SSPL_STORE_TYPE = 'file'
SYSLOG_HOST = 'localhost'
SYSLOG_PORT = 514
SYSINFO = "SYSTEM_INFORMATION"
PRODUCT = "product"
SETUP = "setup"
MAX_CONSUL_RETRY = 12
WAIT_BEFORE_RETRY = 5
SUPPORT_REQUESTOR_NAME = "cortx-support"
SUPPORT_EMAIL_ID = "support@seagate.com"
SUPPORT_CONTACT_NUMBER = "18007324283"
ENCL_TRIGGER_LOG_MAX_RETRY = 10
ENCL_DOWNLOAD_LOG_MAX_RETRY = 60
ENCL_DOWNLOAD_LOG_WAIT_BEFORE_RETRY = 15
PRODUCT_BASE_DIR = "/opt/seagate/%s/" % (PRODUCT_FAMILY)
SSPL_BASE_DIR = "%s/sspl" % (PRODUCT_BASE_DIR)
SSPL_CLI_DIR = "%s/low-level/cli" % (SSPL_BASE_DIR)
RSYSLOG_IEM_CONF ="/etc/rsyslog.d/0-iemfwd.conf"
RSYSLOG_SSPL_CONF = "/etc/rsyslog.d/1-ssplfwd.conf"
LOGROTATE_DIR = "/etc/logrotate.d"
IEM_LOGROTATE_CONF = "%s/iem_messages" % LOGROTATE_DIR
SSPL_LOGROTATE_CONF = "%s/sspl_logs" % LOGROTATE_DIR
SSPL_LOG_PATH = "/var/log/%s/sspl/" % PRODUCT_FAMILY
SSPL_BUNDLE_PATH = "/var/%s/sspl/bundle/" % PRODUCT_FAMILY
HPI_PATH = '/tmp/dcs/hpi'
MDADM_PATH = '/etc/mdadm.conf'
PRVSNR_CONFIG_INDEX = "prvsnr_input_config"
GLOBAL_CONFIG_INDEX = "GLOBAL"
SSPL_CONFIG_INDEX = "SSPL"
SSPL_TEST_CONFIG_INDEX = "SSPL_TEST"
CONFIG_SPEC_TYPE = "yaml"

# This file will be created when sspl is being configured for node replacement case
REPLACEMENT_NODE_ENV_VAR_FILE = "/etc/profile.d/set_replacement_env.sh"

# required only for init
component = 'sspl/config'
file_store_config_path = '/etc/sspl.conf'
sspl_test_file_path = "%s/sspl_test/conf/sspl_tests.conf" % (SSPL_BASE_DIR)
global_config_file_path = "/etc/sspl_global_config_copy.%s" % (CONFIG_SPEC_TYPE)
sspl_config_path = "%s://%s" % (CONFIG_SPEC_TYPE, file_store_config_path)
sspl_test_config_path = "%s://%s" % (CONFIG_SPEC_TYPE, sspl_test_file_path)
global_config_path = "%s://%s" %(CONFIG_SPEC_TYPE, global_config_file_path)
salt_provisioner_pillar_sls = 'sspl'
salt_uniq_attr_per_node = ['cluster_id']
salt_uniq_passwd_per_node = ['INGRESSPROCESSOR', 'EGRESSPROCESSOR', 'LOGGINGPROCESSOR']

# Initialize to default values
node_key_id = 'srvnode-1'
CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'

# TODO Keep only constants in this file.
# other values(configs) should come from config.

# If SSPL is not configured, use salt interface
if not os.path.exists(SSPL_CONFIGURED) and PRODUCT_NAME=="LDR_R1":
    try:
        salt_int = SaltInterface()
        node_key_id = salt_int.get_node_id()
        CONSUL_HOST = salt_int.get_consul_vip()
        CONSUL_PORT = salt_int.get_consul_port()
    except Exception as err:
        print('sspl_constants : Failed to read from SaltInterface due to error - %s' % (err))

CONSUL_ERR_STRING = '500 No cluster leader'

SSPL_SETTINGS = {
        "REALSTORSENSORS": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": [],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["RealStorFanSensor", "RealStorPSUSensor",
                "RealStorControllerSensor", "RealStorDiskSensor", "RealStorSideplaneExpanderSensor",
                "RealStorLogicalVolumeSensor", "RealStorEnclosureSensor"],
        },
        "NODEHWSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": [ "NodeHWsensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": [ "NodeHWsensor"],
        },
        "DISKMONITOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": [],
            "MESSAGE_HANDLERS": [],
            "SENSORS": [],
        },
        "RAIDSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": ["RAIDsensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["RAIDsensor", "RAIDIntegritySensor"],
        },
        "SASPORTSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": ["SASPortSensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["SASPortSensor"],
        },
        "MEMFAULTSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": ["MemFaultSensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["MemFaultSensor"],
        },
        "CPUFAULTSENSOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": ["CPUFaultSensor"],
            "MESSAGE_HANDLERS": [],
            "SENSORS": ["CPUFaultSensor"],
        },
        "SERVICEMONITOR": {
            "ACTUATORS": [],
            "CORE_PROCESSORS": [],
            "DEGRADED_STATE_MODULES": [],
            "MESSAGE_HANDLERS": [],
            "SENSORS": [],
        },

        "_ENABLE_ALWAYS": {
            "ACTUATORS" : ["Service", "RAIDactuator", "Smartctl", "NodeHWactuator", "RealStorActuator"],
            "CORE_PROCESSORS" : ("EgressProcessor", "IngressProcessor", "LoggingProcessor"),
            "DEGRADED_STATE_MODULES" : ("ServiceWatchdog", "NodeData", "IEMSensor",
                "DiskMsgHandler", "LoggingMsgHandler", "ServiceMsgHandler", "NodeDataMsgHandler",
                "NodeControllerMsgHandler"),
            "MESSAGE_HANDLERS" : ("DiskMsgHandler", "LoggingMsgHandler", "ServiceMsgHandler", "NodeDataMsgHandler",
                "NodeControllerMsgHandler", "RealStorEnclMsgHandler", "RealStorActuatorMsgHandler"),
            "SENSORS" : ["DiskMonitor", "ServiceMonitor", "NodeData",  "IEMSensor"]
        }
}

# The keys which are actually active
sspl_settings_configured_groups = set()

if SSPL_STORE_TYPE == 'consul':
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
        "BMC": {
            "sspl_key" : "key_provided_by_provisioner",
            f"ip_{node_key_id}" : f"{node_key_id}/ip",
            f"user_{node_key_id}" : f"{node_key_id}/user",
            f"secret_{node_key_id}" : f"{node_key_id}/secret"
        }
    }
else:
    COMMON_CONFIGS = {
        "SYSTEM_INFORMATION": {
            "sspl_key" : "key_provided_by_provisioner",
            "operating_system" : "operating_system",
            "kernel_version" : "kernel_version",
            "product" : "product",
            "site_id" : "site_id",
            "rack_id" : "rack_id",
            "node_id" : "node_id",
            "cluster_id" : "cluster_id",
            "syslog_host" : "syslog_host",
            "syslog_port" : "syslog_port",
            "setup" : "setup",
            "data_path" : "data_path"
        },
        "STORAGE_ENCLOSURE": {
            "sspl_key" : "key_provided_by_provisioner",
            "primary_controller_ip" : "primary_controller_ip",
            "primary_controller_port" : "primary_controller_port",
            "secondary_controller_ip" : "secondary_controller_ip",
            "secondary_controller_port" : "secondary_controller_port",
            "user" : "user",
            "password" : "password",
            "mgmt_interface" : "mgmt_interface"
        },
        "BMC": {
            "sspl_key" : "key_provided_by_provisioner",
            f"ip" : f"ip",
            f"user" : f"user",
            f"secret" : f"secret"
        }
    }


SSPL_CONFIGS = ['log_level', 'cli_type', 'sspl_log_file_path', 'cluster_id', 'storage_enclosure', 'setup', 'operating_system']


class RaidDataConfig(Enum):
    MDSTAT_FILE = "/proc/mdstat"
    DIR = "/sys/block/"
    SYNC_ACTION_FILE = "/md/sync_action"
    MISMATCH_COUNT_FILE = "/md/mismatch_cnt"
    STATE_COMMAND_RESPONSE = 'idle'
    MISMATCH_COUNT_RESPONSE = '0'
    RAID_RESULT_DIR = f"{DATA_PATH}raid_integrity/"
    RAID_RESULT_FILE_PATH = f"{RAID_RESULT_DIR}result_raid_health_file"
    RAID_MISMATCH_FAULT_STATUS = "mismatch_cnt_fault_status"
    MAX_RETRIES = 10
    NEXT_ITERATION_TIME = 3600
    PRIORITY = 1

class RaidAlertMsgs(Enum):
    MISMATCH_MSG = "MISMATCH COUNT is found, as count does not match to the default '0' value."


class AlertTypes(Enum):
    GET = "get"
    FAULT = "fault"
    FAULT_RESOLVED = "fault_resolved"


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
    CLUSTER = "cluster"
    SERVER_NODE = "server_node"

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
    "I": AlertTypes.FAULT_RESOLVED.value,
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
