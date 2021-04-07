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

from framework.utils.utility import Utility

# Indexes
GLOBAL_CONF = "GLOBAL"
SSPL_CONF = "SSPL"

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
EGRESSPROCESSOR="EGRESSPROCESSOR"
INGRESSPROCESSOR="INGRESSPROCESSOR"
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
DISKMONITOR="DISKMONITOR"
SERVICEMONITOR="SERVICEMONITOR"
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
PRODUCT_NAME = 'product'
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
NODE_TYPE="node_type"
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
TARGET_BUILD="target_build"

# Get SRVNODE and ENCLOSURE so it can be used in other files to get
# server_node and enclosure specific config
utility = Utility()
MACHINE_ID = utility.get_machine_id()
OPERATING_SYSTEM = utility.get_os()

Conf.load(SSPL_CONF, "yaml:///etc/sspl.conf")
global_config = Conf.get(SSPL_CONF, "SYSTEM_INFORMATION>global_config_copy_url")
Conf.load(GLOBAL_CONF, global_config)

SRVNODE = Conf.get(GLOBAL_CONF, "server_node>%s>name" % MACHINE_ID)
ENCLOSURE = Conf.get(GLOBAL_CONF, "server_node>%s>storage>enclosure_id" % MACHINE_ID)

PRODUCT_KEY = "cortx>release>product"
SETUP_KEY = "cortx>release>setup"
SITE_ID_KEY = "server_node>%s>site_id" % MACHINE_ID
NODE_ID_KEY = "server_node>%s>node_id" % MACHINE_ID
RACK_ID_KEY = "server_node>%s>rack_id" % MACHINE_ID
CLUSTER_ID_KEY = "server_node>%s>cluster_id" % MACHINE_ID
STORAGE_SET_ID_KEY = "server_node>%s>storage_set_id" % MACHINE_ID
NODE_TYPE_KEY = "server_node>%s>type" % MACHINE_ID
STORAGE_TYPE_KEY = "storage_enclosure>%s>type" % ENCLOSURE
CNTRLR_PRIMARY_IP_KEY = "storage_enclosure>%s>controller>primary>ip" % ENCLOSURE
CNTRLR_PRIMARY_PORT_KEY = "storage_enclosure>%s>controller>primary>port" % ENCLOSURE
CNTRLR_SECONDARY_IP_KEY = "storage_enclosure>%s>controller>secondary>ip" % ENCLOSURE
CNTRLR_SECONDARY_PORT_KEY = "storage_enclosure>%s>controller>secondary>port" % ENCLOSURE
CNTRLR_USER_KEY = "storage_enclosure>%s>controller>user" % ENCLOSURE
CNTRLR_PASSWD_KEY = "storage_enclosure>%s>controller>secret" % ENCLOSURE
BMC_IP_KEY = "server_node>%s>bmc>ip" % MACHINE_ID
BMC_USER_KEY = "server_node>%s>bmc>user" % MACHINE_ID
BMC_SECRET_KEY = "server_node>%s>bmc>secret" % MACHINE_ID
