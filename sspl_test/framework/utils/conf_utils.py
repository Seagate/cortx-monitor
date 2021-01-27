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

# Indexes
GLOBAL_CONF = "GLOBAL"
SSPL_CONF = "SSPL"
SSPL_TEST_CONF = "SSPL-Test"

# Keys constans
BMC_INTERFACE="BMC_INTERFACE"
CPUFAULTSENSOR="CPUFAULTSENSOR"
DATASTORE="DATASTORE"
DISKMSGHANDLER="DISKMSGHANDLER"
IEMSENSOR="IEMSENSOR"
IPMI="IPMI"
LOGGINGMSGHANDLER="LOGGINGMSGHANDLER"
LOGGINGPROCESSOR="LOGGINGPROCESSOR"
MEMFAULTSENSOR="MEMFAULTSENSOR"
NODEDATAMSGHANDLER="NODEDATAMSGHANDLER"
NODEHWACTUATOR="NODEHWACTUATOR"
NODEHWSENSOR="NODEHWSENSOR"
RABBITMQCLUSTER="RABBITMQCLUSTER"
RABBITMQEGRESSPROCESSOR="RABBITMQEGRESSPROCESSOR"
RABBITMQINGRESSPROCESSOR="RABBITMQINGRESSPROCESSOR"
RAIDSENSOR="RAIDSENSOR"
RAID_STATUS_FILE="RAID_status_file"
REALSTORCONTROLLERSENSOR="REALSTORCONTROLLERSENSOR"
REALSTORDISKSENSOR="REALSTORDISKSENSOR"
REALSTORENCLOSURESENSOR="REALSTORENCLOSURESENSOR"
REALSTORFANSENSOR="REALSTORFANSENSOR"
REALSTORLOGICALVOLUMESENSOR="REALSTORLOGICALVOLUMESENSOR"
REALSTORPSUSENSOR="REALSTORPSUSENSOR"
REALSTORSENSORS="REALSTORSENSORS"
REALSTORSIDEPLANEEXPANDERSENSOR="REALSTORSIDEPLANEEXPANDERSENSOR"
SASPORTSENSOR="SASPORTSENSOR"
SSPL_LL_SETTING="SSPL_LL_SETTING"
STORAGE_ENCLOSURE="STORAGE_ENCLOSURE"
SYSTEMDWATCHDOG="SYSTEMDWATCHDOG"
SYSTEM_INFORMATION="SYSTEM_INFORMATION"
ACK_EXCHANGE_NAME="ack_exchange_name"
ACK_QUEUE_NAME="ack_queue_name"
ACK_ROUTING_KEY="ack_routing_key"
ACTUATORS="actuators"
ALWAYS_LOG_IEM="always_log_iem"
BMC="bmc"
CLI_TYPE="cli_type"
CLUSTER="cluster"
CLUSTER_ID="cluster_id"
CLUSTER_NODES="cluster_nodes"
CONSUL_HOST="consul_host"
CONSUL_PORT="consul_port"
CONTROLLER="controller"
CORE_PROCESSORS="core_processors"
CPU_USAGE_THRESHOLD="cpu_usage_threshold"
DATA_PATH_KEY="data_path"
DEFAULT="default"
DEGRADED_STATE_MODULES="degraded_state_modules"
DISK_USAGE_THRESHOLD="disk_usage_threshold"
DMREPORT_FILE="dmreport_file"
ENCLOSURE_ID="enclosure_id"
ERLANG_COOKIE="erlang_cookie"
EXCHANGE_NAME="exchange_name"
HOST="host"
HOST_MEMORY_USAGE_THRESHOLD="host_memory_usage_threshold"
IEM_LOG_LOCALLY="iem_log_locally"
IEM_ROUTE_ADDR="iem_route_addr"
IEM_ROUTE_EXCHANGE_NAME="iem_route_exchange_name"
IEM_ROUTING_ENABLED="iem_routing_enabled"
IP="ip"
IPMI_CLIENT="ipmi_client"
LIMIT_CONSUL_MEMORY="limit_consul_memory"
LOG_FILE_PATH="log_file_path"
LOG_LEVEL="log_level"
MAX_DRIVEMANAGER_EVENT_INTERVAL="max_drivemanager_event_interval"
MAX_DRIVEMANAGER_EVENTS="max_drivemanager_events"
MESSAGE_HANDLERS="message_handlers"
MESSAGE_SIGNATURE_EXPIRES="message_signature_expires"
MESSAGE_SIGNATURE_TOKEN="message_signature_token"
MESSAGE_SIGNATURE_USERNAME="message_signature_username"
MGMT_INTERFACE="mgmt_interface"
MONITOR="monitor"
MONITORED_SERVICES="monitored_services"
NODE_ID="node_id"
PASS="pass"
PASSWORD="password"
POLLING_FREQUENCY="polling_frequency"
POLLING_FREQUENCY_OVERRIDE="polling_frequency_override"
POLLING_INTERVAL="polling_interval"
PORT="port"
PRIMARY="primary"
PRIMARY_RABBITMQ_HOST="primary_rabbitmq_host"
PROBE="probe"
PRODUCT="product"
QUEUE_NAME="queue_name"
RACK_ID="rack_id"
RELEASE="release"
ROUTING_KEY="routing_key"
RSYSLOG="rsyslog"
RUN_SMART_ON_START="run_smart_on_start"
SECONDARY="secondary"
SECRET="secret"
SENSORS="sensors"
SERVER_NODES="server_nodes"
SETUP="setup"
SITE_ID="site_id"
SMART_TEST_INTERVAL="smart_test_interval"
SSPL_LOG_FILE_PATH="sspl_log_file_path"
STORAGE="storage"
STORAGE_SET_ID="storage_set_id"
STORE_TYPE="store_type"
THREADED="threaded"
TIMESTAMP_FILE_PATH="timestamp_file_path"
TRANSMIT_INTERVAL="transmit_interval"
TYPE="type"
UNITS="units"
USER="user"
USERNAME="username"
VIRTUAL_HOST="virtual_host"

# Get SRVNODE and ENCLOSURE so it can be used in other files to get
# server_node and enclosure specific config
with open("/etc/machine-id") as f:
    MACHINE_ID = f.read().strip("\n")

Conf.load(GLOBAL_CONF, "yaml:///etc/sample_global_cortx_config.yaml")
Conf.load(SSPL_CONF, "yaml:///etc/sspl.conf")
Conf.load(SSPL_TEST_CONF, "yaml:///opt/seagate/cortx/sspl/sspl_test/conf/sspl_tests.conf.yaml")

SRVNODE = Conf.get("GLOBAL", f'{CLUSTER}>{SERVER_NODES}')[MACHINE_ID]
ENCLOSURE = Conf.get("GLOBAL", f"{CLUSTER}>{SRVNODE}>{STORAGE}>{ENCLOSURE_ID}")
