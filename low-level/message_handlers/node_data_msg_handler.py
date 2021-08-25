# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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

"""
 ****************************************************************************
  Description:       Message Handler for requesting node data
 ****************************************************************************
"""

import json
import time
import os

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.base.sspl_constants import enabled_products, DATA_PATH
from framework.utils.conf_utils import (GLOBAL_CONF, SSPL_CONF, Conf,
                                        NODE_ID_KEY)
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from json_msgs.messages.sensors.cpu_data import CPUdataMsg
from json_msgs.messages.sensors.disk_space_alert import DiskSpaceAlertMsg
from json_msgs.messages.sensors.host_update import HostUpdateMsg
from json_msgs.messages.sensors.if_data import IFdataMsg
from json_msgs.messages.sensors.local_mount_data import LocalMountDataMsg
from json_msgs.messages.sensors.node_hw_data import NodeIPMIDataMsg
from json_msgs.messages.sensors.raid_data import RAIDdataMsg
from json_msgs.messages.sensors.raid_integrity_msg import RAIDIntegrityMsg
from framework.messaging.egress_processor import EgressProcessor
from framework.utils.store_factory import file_store
from framework.utils.utility import Utility

# Override default store
store = file_store

class NodeDataMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for generic node requests and generating
        host update messages on a regular interval"""

    MODULE_NAME = "NodeDataMsgHandler"
    PRIORITY    = 2

    # Section and keys in configuration file
    NODEDATAMSGHANDLER = MODULE_NAME.upper()
    TRANSMIT_INTERVAL = 'transmit_interval'
    HIGH_CPU_USAGE_WAIT_THRESHOLD = 'high_cpu_usage_wait_threshold'
    HIGH_MEMORY_USAGE_WAIT_THRESHOLD = 'high_memory_usage_wait_threshold'
    UNITS = 'units'
    DISK_USAGE_THRESHOLD = 'disk_usage_threshold'
    DEFAULT_DISK_USAGE_THRESHOLD = 80
    CPU_USAGE_THRESHOLD = 'cpu_usage_threshold'
    DEFAULT_CPU_USAGE_THRESHOLD = 80
    HOST_MEMORY_USAGE_THRESHOLD = 'host_memory_usage_threshold'
    DEFAULT_HOST_MEMORY_USAGE_THRESHOLD = 80

    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"

    IPMI_RESOURCE_TYPE_PSU = "node:hw:psu"
    IPMI_RESOURCE_TYPE_FAN = "node:hw:fan"
    IPMI_RESOURCE_TYPE_DISK = "node:hw:disk"
    IPMI_RESOURCE_TYPE_TEMPERATURE = "node:sensor:temperature"
    IPMI_RESOURCE_TYPE_VOLTAGE = "node:sensor:voltage"
    IPMI_RESOURCE_TYPE_CURRENT = "node:sensor:current"
    NW_RESOURCE_TYPE = "node:interface:nw"
    NW_CABLE_RESOURCE_TYPE = "node:interface:nw:cable"
    high_usage = {
        'cpu' : False,
        'disk' : False,
        'memory' : False
    }
    usage_time_map = {
        'cpu' : -1,
        'memory' : -1,
        'disk' : -1
    }
    fault_resolved_iterations = {
        'cpu': 0,
        'memory': 0,
        'disk': 0
    }
    prev_nw_status = {}
    prev_cable_status = {}
    FAULT = "fault"
    FAULT_RESOLVED = "fault_resolved"

    INTERFACE_FAULT_DETECTED = False

    CACHE_DIR_NAME = "server"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["EgressProcessor"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """ @return: name of the module."""
        return NodeDataMsgHandler.MODULE_NAME

    def __init__(self):
        super(NodeDataMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        # Flag to indicate suspension of module
        self._suspended = False

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return NodeDataMsgHandler.DEPENDENCIES

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(NodeDataMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(NodeDataMsgHandler, self).initialize_msgQ(msgQlist)

        self._transmit_interval = int(Conf.get(SSPL_CONF, f"{self.NODEDATAMSGHANDLER}>{self.TRANSMIT_INTERVAL}",
                                               60))
        self._high_cpu_usage_wait_threshold = int(Conf.get(SSPL_CONF,
                                                f"{self.NODEDATAMSGHANDLER}>{self.HIGH_CPU_USAGE_WAIT_THRESHOLD}",60))
        self._high_memory_usage_wait_threshold = int(Conf.get(SSPL_CONF,
                                                f"{self.NODEDATAMSGHANDLER}>{self.HIGH_MEMORY_USAGE_WAIT_THRESHOLD}",60))
        self._units = Conf.get(SSPL_CONF, f"{self.NODEDATAMSGHANDLER}>{self.UNITS}",
                                                "MB")
        self._disk_usage_threshold = Conf.get(SSPL_CONF, f"{self.NODEDATAMSGHANDLER}>{self.DISK_USAGE_THRESHOLD}",
                                                self.DEFAULT_DISK_USAGE_THRESHOLD)

        self._cpu_usage_threshold = Conf.get(SSPL_CONF, f"{self.NODEDATAMSGHANDLER}>{self.CPU_USAGE_THRESHOLD}",
                                                self.DEFAULT_CPU_USAGE_THRESHOLD)

        self._host_memory_usage_threshold = Conf.get(SSPL_CONF, f"{self.NODEDATAMSGHANDLER}>{self.HOST_MEMORY_USAGE_THRESHOLD}",
                                                self.DEFAULT_HOST_MEMORY_USAGE_THRESHOLD)

        self.node_id = Conf.get(GLOBAL_CONF, NODE_ID_KEY, "SN01")

        self.bmcNwStatus = None
        self.severity_reader = SeverityReader()
        self._node_sensor    = None
        self._login_actuator = None
        self.disk_sensor_data = None
        self.host_sensor_data = None
        self.if_sensor_data = None
        self.cpu_sensor_data = None
        self.raid_sensor_data = None
        self.sensor_type = None
        self._epoch_time = str(int(time.time()))
        self._raid_drives = []
        self._raid_device = "N/A"
        self.os_sensor_type = {
            "disk_space" : self.disk_sensor_data,
            "memory_usage" : self.host_sensor_data,
            "nw"   : self.if_sensor_data,
            "cpu_usage"  : self.cpu_sensor_data,
            "raid_data" : self.raid_sensor_data
        }

        # UUID used in json msgs
        self._uuid = None

        # Dict of drives by device name from systemd
        self._drive_by_device_name = {}

        # Dict of drive path by-ids by serial number from systemd
        self._drive_byid_by_serial_number = {}

        self._import_products(product)
        self.cache_dir_path = os.path.join(DATA_PATH, self.CACHE_DIR_NAME)

        self.persistent_data = {
            'cpu' : {},
            'disk' : {},
            'memory' : {},
            'nw' : {}
        }
        # Persistent Cache for High CPU usage
        self.init_from_persistent_cache('cpu', 'CPU_USAGE_DATA')
        # Persistent Cache for High Disk Usage
        self.init_from_persistent_cache('disk', 'DISK_USAGE_DATA')
        # Persistent Cache for High Memory Usage
        self.init_from_persistent_cache('memory', 'MEMORY_USAGE_DATA')
        # Persistent Cache for Nework sensor
        self.init_from_persistent_cache('nw', 'NW_SENSOR_DATA')

    def init_from_persistent_cache(self, resource, data_path):
        PER_DATA_PATH = os.path.join(self.cache_dir_path,
                            f'{data_path}_{self.node_id}')

        if os.path.isfile(PER_DATA_PATH):
            self.persistent_data[resource] = store.get(PER_DATA_PATH)
        if self.persistent_data[resource]:
            if resource == 'nw':
                self.prev_nw_status = \
                    self.persistent_data[resource].get('prev_nw_status', {})
                self.prev_cable_status = \
                    self.persistent_data[resource].get('prev_cable_status', {})
            elif self.persistent_data[resource]\
                [f'high_{resource}_usage'].lower() == "true":
                self.high_usage[resource] = True
            else:
                self.high_usage[resource] = False
        else:
            self.persist_state_data(resource, data_path)

    def persist_state_data(self, resource, data_path):
        PER_DATA_PATH = os.path.join(self.cache_dir_path,
                            f'{data_path}_{self.node_id}')
        if resource == 'nw':
            self.persistent_data[resource] = {
                'prev_nw_status': self.prev_nw_status,
                'prev_cable_status': self.prev_cable_status
            }
        else:
            self.persistent_data[resource] = {
                f'high_{resource}_usage': str(self.high_usage[resource]),
                f'{resource}_usage_time_map':
                    str(self.usage_time_map[resource]),
                f'{resource}_fault_resolved_iterations':
                    str(self.fault_resolved_iterations[resource])
            }
        store.put(self.persistent_data[resource], PER_DATA_PATH)

    def read_persistent_data(self, data_path):
        """Read resource data from persistent cache."""
        persistent_data = {}
        PER_DATA_PATH = os.path.join(self.cache_dir_path,
                            f'{data_path}_{self.node_id}')
        if os.path.isfile(PER_DATA_PATH):
            persistent_data = store.get(PER_DATA_PATH)
        return persistent_data

    def _import_products(self, product):
        """Import classes based on which product is being used"""
        if product.lower() in [x.lower() for x in enabled_products]:
            from zope.component import queryUtility
            self._queryUtility = queryUtility

    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Start accepting requests")

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(1, self._priority, self.run, ())
            return

        # self._set_debug(True)
        # self._set_debug_persist(True)

        try:
            # Query the Zope GlobalSiteManager for an object implementing INodeData
            if self._node_sensor is None:
                from sensors.INode_data import INodeData
                self._node_sensor = self._queryUtility(INodeData)()
                self._log_debug("_node_sensor name: %s" % self._node_sensor.name())

            # Delay for the desired interval if it's greater than zero
            if self._transmit_interval > 0:
                logger.debug("self._transmit_interval:{}".format(self._transmit_interval))
                timer = self._transmit_interval
                while timer > 0:
                    # See if the message queue contains an entry and process
                    jsonMsg, _ = self._read_my_msgQ_noWait()
                    if jsonMsg is not None:
                        self._process_msg(jsonMsg)

                    time.sleep(1)
                    timer -= 1

                # Generate the JSON messages with data from the node and transmit on regular interval
                self._generate_host_update()
                self._generate_cpu_data()
                self._generate_if_data()
                self._generate_disk_space_alert()

            # If the timer is zero then block for incoming requests notifying to transmit data
            else:
                # Block on message queue until it contains an entry
                jsonMsg, _ = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._process_msg(jsonMsg)

                # Keep processing until the message queue is empty
                while not self._is_my_msgQ_empty():
                    jsonMsg, _ = self._read_my_msgQ()
                    if jsonMsg is not None:
                        self._process_msg(jsonMsg)

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception("NodeDataMsgHandler restarting: %s" % ae)

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and generate the desired data message"""
        self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        # Parse out the uuid so that it can be sent back in response message
        self._uuid = None
        if jsonMsg.get("sspl_ll_msg_header") is not None and \
           jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            self._uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            self._log_debug("_processMsg, uuid: %s" % self._uuid)

        if jsonMsg.get("sensor_request_type") is not None and \
           jsonMsg.get("sensor_request_type").get("node_data") is not None and \
           jsonMsg.get("sensor_request_type").get("node_data").get("sensor_type") is not None:
            self.sensor_type = jsonMsg.get("sensor_request_type").get("node_data").get("sensor_type").split(":")[2]
            self._log_debug("_processMsg, sensor_type: %s" % self.sensor_type)

            if self.sensor_type == "memory_usage":
                self._generate_host_update()
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(EgressProcessor.name(),
                                          sensor_message_type)
                else:
                    self._log_debug(f"NodeDataMsgHandler, _process_msg, \
                        No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "cpu_usage":
                self._generate_cpu_data()
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(EgressProcessor.name(),
                                          sensor_message_type)
                else:
                    self._log_debug(f"NodeDataMsgHandler, _process_msg, \
                        No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "nw":
                self._generate_if_data()
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(EgressProcessor.name(),
                                          sensor_message_type)
                else:
                    self._log_debug(f"NodeDataMsgHandler, _process_msg, \
                        No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "disk_space":
                self._generate_disk_space_alert()
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(EgressProcessor.name(),
                                          sensor_message_type)
                else:
                    self._log_debug(f"NodeDataMsgHandler, _process_msg, \
                        No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "raid_data":
                self._generate_raid_data(jsonMsg)
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(EgressProcessor.name(),
                                            sensor_message_type)
                else:
                    self._log_debug("NodeDataMsgHandler, _process_msg " +
                            f"No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "raid_integrity":
                self._generate_raid_integrity_data(jsonMsg)
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(EgressProcessor.name(),
                                            sensor_message_type)
                else:
                    self._log_debug("NodeDataMsgHandler, _process_msg " +
                            f"No past data found for {self.sensor_type} sensor type")


        # Update mapping of device names to serial numbers for global use
        elif jsonMsg.get("sensor_response_type") is not None:
            if jsonMsg.get("sensor_response_type") == "devicename_serialnumber":
                self._update_devicename_sn_dict(jsonMsg)
        elif jsonMsg.get("sensor_request_type") is not None and \
            jsonMsg.get("sensor_request_type").get("node_data") is not None and \
            jsonMsg.get("sensor_request_type").get("node_data").get("info") is not None and \
            jsonMsg.get("sensor_request_type").get("node_data").get("info").get("resource_type") is not None:
                self._generate_node_fru_data(jsonMsg)

        # ... handle other node sensor message types

    def _update_devicename_sn_dict(self, jsonMsg):
        """Update the dict of device names to serial numbers"""
        drive_byid = jsonMsg.get("drive_byid")
        device_name = jsonMsg.get("device_name")
        serial_number = jsonMsg.get("serial_number")

        self._drive_by_device_name[device_name] = serial_number
        self._drive_byid_by_serial_number[serial_number] = drive_byid

        self._log_debug("NodeDataMsgHandler, device_name: %s, serial_number: %s, drive_byid: %s" %
                        (device_name, serial_number, drive_byid))

    def _generate_host_update(self):
        """Create & transmit a host update message as defined
            by the sensor response json schema"""

        current_time = Utility.get_current_time()

        # Notify the node sensor to update its data required for the host_update message
        successful = self._node_sensor.read_data("host_update", self._get_debug(), self._units)
        if not successful:
            logger.error("NodeDataMsgHandler, _generate_host_update was NOT successful.")

        self._host_memory_usage_threshold = str(self._host_memory_usage_threshold)
        try:
            if self._host_memory_usage_threshold.isdigit():
                self._host_memory_usage_threshold = int(self._host_memory_usage_threshold)
            else:
                self._host_memory_usage_threshold = float(self._host_memory_usage_threshold)
        except ValueError:
            logger.warning("Host Memory Alert, Invalid host_memory_usage_threshold value are entered in config.")
            # Assigning default value to _memory_usage_threshold
            self._host_memory_usage_threshold = self.DEFAULT_HOST_MEMORY_USAGE_THRESHOLD

        memory_persistent_data = self.read_persistent_data('MEMORY_USAGE_DATA')
        if memory_persistent_data.get('memory_usage_time_map') is not None:
            previous_check_time = int(memory_persistent_data['memory_usage_time_map'])
        else:
            previous_check_time = int(-1)
        if memory_persistent_data\
                .get('memory_fault_resolved_iterations') is not None:
            fault_resolved_iters = int(
                memory_persistent_data['memory_fault_resolved_iterations'])
        else:
            fault_resolved_iters = 0
        try:
            iteration_limit = int(
                self._high_memory_usage_wait_threshold/self._transmit_interval)
        except ZeroDivisionError:
            iteration_limit = 0
        self.usage_time_map['memory'] = current_time

        if self._node_sensor.total_memory["percent"] >= self._host_memory_usage_threshold \
           and not self.high_usage['memory']:
            if previous_check_time == -1:
                previous_check_time = current_time
                self.persist_state_data('memory', 'MEMORY_USAGE_DATA')

            if self.usage_time_map['memory'] - previous_check_time >= self._high_memory_usage_wait_threshold:
                self.high_usage['memory'] = True
                self.fault_resolved_iterations['memory'] = 0
                # Create the memory data message and hand it over
                # to the egress processor to transmit
                fault_event = "Host memory usage has increased to {}%,"\
                    "beyond the configured threshold of {}% "\
                    "for more than {} seconds.".format(
                        self._node_sensor.total_memory["percent"],
                        self._host_memory_usage_threshold,
                        self._high_memory_usage_wait_threshold
                    )

                logger.warning(fault_event)

                logged_in_users = []
                # Create the host update message and hand it over to the egress processor to transmit
                hostUpdateMsg = HostUpdateMsg(self._node_sensor.host_id,
                                        self._epoch_time,
                                        self._node_sensor.boot_time,
                                        self._node_sensor.up_time,
                                        self._node_sensor.uname, self._units,
                                        self._node_sensor.total_memory,
                                        self._node_sensor.logged_in_users,
                                        self._node_sensor.process_count,
                                        self._node_sensor.running_process_count,
                                        self.FAULT,
                                        fault_event
                                        )
                # Add in uuid if it was present in the json request
                if self._uuid is not None:
                    hostUpdateMsg.set_uuid(self._uuid)
                jsonMsg = hostUpdateMsg.getJson()
                # Transmit it to message processor
                self.host_sensor_data = jsonMsg
                self.os_sensor_type["memory_usage"] = self.host_sensor_data
                self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)
                self.persist_state_data('memory', 'MEMORY_USAGE_DATA')

        if self._node_sensor.total_memory["percent"] < self._host_memory_usage_threshold:
            if not self.high_usage['memory']:
                self.persist_state_data('memory', 'MEMORY_USAGE_DATA')
            else:
                if fault_resolved_iters < iteration_limit:
                    fault_resolved_iters += 1
                    self.fault_resolved_iterations['memory'] = fault_resolved_iters
                    self.persist_state_data('memory', 'MEMORY_USAGE_DATA')
                elif fault_resolved_iters >= iteration_limit:
                    # Create the memory data message and hand it over
                    # to the egress processor to transmit
                    fault_resolved_event = "Host memory usage has decreased to {}%, "\
                        "lower than the configured threshold of {}%.".format(
                            self._node_sensor.total_memory["percent"],
                            self._host_memory_usage_threshold
                        )
                    logger.info(fault_resolved_event)
                    logged_in_users = []

                    # Create the host update message and hand it over to the egress processor to transmit
                    hostUpdateMsg = HostUpdateMsg(self._node_sensor.host_id,
                                            self._epoch_time,
                                            self._node_sensor.boot_time,
                                            self._node_sensor.up_time,
                                            self._node_sensor.uname, self._units,
                                            self._node_sensor.total_memory,
                                            self._node_sensor.logged_in_users,
                                            self._node_sensor.process_count,
                                            self._node_sensor.running_process_count,
                                            self.FAULT_RESOLVED,
                                            fault_resolved_event
                                            )

                    # Add in uuid if it was present in the json request
                    if self._uuid is not None:
                        hostUpdateMsg.set_uuid(self._uuid)
                    jsonMsg = hostUpdateMsg.getJson()
                    # Transmit it to message processor
                    self.host_sensor_data = jsonMsg
                    self.os_sensor_type["memory_usage"] = self.host_sensor_data
                    self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)
                    self.high_usage['memory'] = False
                    self.usage_time_map['memory'] = int(-1)
                    self.fault_resolved_iterations['memory'] = 0
                    self.persist_state_data('memory', 'MEMORY_USAGE_DATA')

    def _generate_local_mount_data(self):
        """Create & transmit a local_mount_data message as defined
            by the sensor response json schema"""

        # Notify the node sensor to update its data required for the local_mount_data message
        successful = self._node_sensor.read_data("local_mount_data", self._get_debug(), self._units)
        if not successful:
            logger.error("NodeDataMsgHandler, _generate_local_mount_data was NOT successful.")

        # Create the local mount data message and hand it over to the egress processor to transmit
        localMountDataMsg = LocalMountDataMsg(self._node_sensor.host_id,
                                self._epoch_time,
                                self._node_sensor.free_space,
                                self._node_sensor.free_inodes,
                                self._node_sensor.free_swap,
                                self._node_sensor.total_space,
                                self._node_sensor.total_swap,
                                self._units)

        # Add in uuid if it was present in the json request
        if self._uuid is not None:
            localMountDataMsg.set_uuid(self._uuid)
        jsonMsg = localMountDataMsg.getJson()

        # Transmit it to message processor
        self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)

    def _generate_cpu_data(self):
        """Create & transmit a cpu_data message as defined
            by the sensor response json schema"""

        current_time = Utility.get_current_time()

        # Notify the node sensor to update its data required for the cpu_data message
        successful = self._node_sensor.read_data("cpu_data", self._get_debug())
        if not successful:
            logger.error("NodeDataMsgHandler, _generate_cpu_data was NOT successful.")

        self._cpu_usage_threshold = str(self._cpu_usage_threshold)
        try:
            if self._cpu_usage_threshold.isdigit():
                self._cpu_usage_threshold = int(self._cpu_usage_threshold)
            else:
                self._cpu_usage_threshold = float(self._cpu_usage_threshold)
        except ValueError:
            logger.warning("CPU Usage Alert, Invalid host_memory_usage_threshold value are entered in config.")
            # Assigning default value to _cpu_usage_threshold
            self._cpu_usage_threshold = self.DEFAULT_CPU_USAGE_THRESHOLD

        cpu_persistent_data = self.read_persistent_data('CPU_USAGE_DATA')
        if cpu_persistent_data.get('cpu_usage_time_map') is not None:
            previous_check_time = int(cpu_persistent_data['cpu_usage_time_map'])
        else:
            previous_check_time = int(-1)
        if cpu_persistent_data.get('cpu_fault_resolved_iterations') is not None:
            fault_resolved_iters = int(
                cpu_persistent_data['cpu_fault_resolved_iterations'])
        else:
            fault_resolved_iters = 0
        try:
            iteration_limit = int(
                self._high_cpu_usage_wait_threshold/self._transmit_interval)
        except ZeroDivisionError:
            iteration_limit = 0
        self.usage_time_map['cpu'] = current_time

        if self._node_sensor.cpu_usage >= self._cpu_usage_threshold \
           and not self.high_usage['cpu']:
            if previous_check_time == -1:
                previous_check_time = current_time
                self.persist_state_data('cpu', 'CPU_USAGE_DATA')

            if self.usage_time_map['cpu'] - previous_check_time >= self._high_cpu_usage_wait_threshold:

                self.high_usage['cpu'] = True
                self.fault_resolved_iterations['cpu'] = 0
                # Create the cpu usage data message and hand it over
                # to the egress processor to transmit
                fault_event = "CPU usage has increased to {}%, "\
                    "beyond the configured threshold of {}% "\
                    "for more than {} seconds.".format(
                        self._node_sensor.cpu_usage,
                        self._cpu_usage_threshold,
                        self._high_cpu_usage_wait_threshold
                    )
                logger.warning(fault_event)

                # Create the cpu usage update message and hand it over to the egress processor to transmit
                cpuDataMsg = CPUdataMsg(self._node_sensor.host_id,
                                    self._epoch_time,
                                    self._node_sensor.csps,
                                    self._node_sensor.idle_time,
                                    self._node_sensor.interrupt_time,
                                    self._node_sensor.iowait_time,
                                    self._node_sensor.nice_time,
                                    self._node_sensor.softirq_time,
                                    self._node_sensor.steal_time,
                                    self._node_sensor.system_time,
                                    self._node_sensor.user_time,
                                    self._node_sensor.cpu_core_data,
                                    self._node_sensor.cpu_usage,
                                    self.FAULT,
                                    fault_event
                                )

                # Add in uuid if it was present in the json request
                if self._uuid is not None:
                    cpuDataMsg.set_uuid(self._uuid)
                jsonMsg = cpuDataMsg.getJson()
                self.cpu_sensor_data = jsonMsg
                self.os_sensor_type["cpu_usage"] = self.cpu_sensor_data

                # Transmit it to message processor
                self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)
                # Store the state to Persistent Cache.
                self.persist_state_data('cpu', 'CPU_USAGE_DATA')

        if self._node_sensor.cpu_usage < self._cpu_usage_threshold:
            if not self.high_usage['cpu']:
                self.persist_state_data('cpu', 'CPU_USAGE_DATA')
            else:
                if fault_resolved_iters < iteration_limit:
                    fault_resolved_iters += 1
                    self.fault_resolved_iterations['cpu'] = fault_resolved_iters
                    self.persist_state_data('cpu', 'CPU_USAGE_DATA')
                elif fault_resolved_iters >= iteration_limit:

                    # Create the cpu usage data message and hand it over
                    # to the egress processor to transmit
                    fault_resolved_event = "CPU usage has decreased to {}%, "\
                        "lower than the configured threshold of {}%.".format(
                            self._node_sensor.cpu_usage,
                            self._cpu_usage_threshold
                        )
                    logger.info(fault_resolved_event)

                    # Create the cpu usage update message and hand it over to the egress processor to transmit
                    cpuDataMsg = CPUdataMsg(self._node_sensor.host_id,
                                        self._epoch_time,
                                        self._node_sensor.csps,
                                        self._node_sensor.idle_time,
                                        self._node_sensor.interrupt_time,
                                        self._node_sensor.iowait_time,
                                        self._node_sensor.nice_time,
                                        self._node_sensor.softirq_time,
                                        self._node_sensor.steal_time,
                                        self._node_sensor.system_time,
                                        self._node_sensor.user_time,
                                        self._node_sensor.cpu_core_data,
                                        self._node_sensor.cpu_usage,
                                        self.FAULT_RESOLVED,
                                        fault_resolved_event
                                    )

                    # Add in uuid if it was present in the json request
                    if self._uuid is not None:
                        cpuDataMsg.set_uuid(self._uuid)
                    jsonMsg = cpuDataMsg.getJson()
                    self.cpu_sensor_data = jsonMsg
                    self.os_sensor_type["cpu_usage"] = self.cpu_sensor_data

                    # Transmit it to message processor
                    self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)
                    self.high_usage['cpu'] = False
                    self.usage_time_map['cpu'] = int(-1)
                    self.fault_resolved_iterations['cpu'] = 0
                    # Store the state to Persistent Cache.
                    self.persist_state_data('cpu', 'CPU_USAGE_DATA')

    def _send_ifdata_json_msg(self, resource_id, resource_type, state, event=""):
        """A resuable method for transmitting IFDataMsg to RMQ and IEM logging"""
        ifDataMsg = IFdataMsg(self._node_sensor.host_id,
                                self._node_sensor.local_time,
                                self._node_sensor.if_data,
                                resource_id,
                                resource_type,
                                state,
                                self.severity_reader.map_severity(state), event)
        # Add in uuid if it was present in the json request
        if self._uuid is not None:
            ifDataMsg.set_uuid(self._uuid)
        jsonMsg = ifDataMsg.getJson()
        self.if_sensor_data = jsonMsg
        self.os_sensor_type["nw"] = self.if_sensor_data

        # Transmit it to message processor
        self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)
        self.persist_state_data('nw', 'NW_SENSOR_DATA')

    def _generate_if_data(self):
        """Create & transmit a network interface data message as defined
            by the sensor response json schema"""
        # Notify the node sensor to update its data required for the if_data message
        successful = self._node_sensor.read_data("if_data", self._get_debug())
        if not successful:
            logger.error("NodeDataMsgHandler, _generate_if_data was NOT successful.")
        interfaces = self._node_sensor.if_data

        cable_alert_desc = "Newtork Cable for interface {} is {}."
        nw_alert_desc = "Network interface {} is {}."

        for interface in interfaces:
            if_name = interface["ifId"]
            nw_status = interface['nwStatus'].upper()
            # if nw_fault
            if nw_status in ["DOWN", "UNKNOWN"]:
                nw_cable_status = interface['nwCableConnStatus'].upper()
                # if nw_cable_disconneted
                if nw_cable_status == "DISCONNECTED":
                    if self.prev_cable_status.get(if_name) != "cable_disconnected":
                        # raise nw_cable_fault_alert
                        self.prev_cable_status[if_name] = "cable_disconnected"
                        self._send_ifdata_json_msg(
                            if_name, self.NW_CABLE_RESOURCE_TYPE, self.FAULT,
                            cable_alert_desc.format(if_name, nw_cable_status))
                # elif nw_cable_connected
                elif nw_cable_status == "CONNECTED":
                    if self.prev_cable_status.get(if_name) == "cable_disconnected":
                        # raise nw_cable_fault_resolved_alert 
                        self.prev_cable_status[if_name] = "cable_connected"
                        self._send_ifdata_json_msg(
                            if_name, self.NW_CABLE_RESOURCE_TYPE,
                            self.FAULT_RESOLVED,
                            cable_alert_desc.format(if_name, nw_cable_status))
                    if self.prev_nw_status.get(if_name) != "nw_down":
                        # raise nw_fault_alert
                        self.prev_nw_status[if_name] = "nw_down"
                        self._send_ifdata_json_msg(
                            if_name, self.NW_RESOURCE_TYPE, self.FAULT,
                            nw_alert_desc.format(if_name, "DOWN")
                        )
                # nw_cable_state is unknown and nw_is_faulty
                else:
                    if self.prev_nw_status.get(if_name) != "nw_down":
                        # raise nw_fault_alert
                        self.prev_nw_status[if_name] = "nw_down"
                        self._send_ifdata_json_msg(
                            if_name, self.NW_RESOURCE_TYPE, self.FAULT,
                            nw_alert_desc.format(if_name, "DOWN")
                        )
            else: # no nw_fault
                if self.prev_nw_status.get(if_name) == "nw_down":
                    # raise nw_fault_resolved_alert
                    self.prev_nw_status[if_name] = "nw_up"
                    self._send_ifdata_json_msg(
                        if_name, self.NW_RESOURCE_TYPE, self.FAULT_RESOLVED,
                        nw_alert_desc.format(if_name, "UP")
                    )
                elif self.prev_cable_status.get(if_name) == "cable_disconnected":
                    # raise nw_cable_fault_resolved_alert
                    self.prev_cable_status[if_name] = "cable_connected"
                    self._send_ifdata_json_msg(
                        if_name, self.NW_CABLE_RESOURCE_TYPE,
                        self.FAULT_RESOLVED,
                        cable_alert_desc.format(if_name, "CONNECTED")
                    )
            
    def _generate_disk_space_alert(self):
        """Create & transmit a disk_space_alert message as defined
            by the sensor response json schema"""

        # Notify the node sensor to update its data required for the disk_space_data message
        successful = self._node_sensor.read_data("disk_space_alert", self._get_debug(), self._units)
        if not successful:
            logger.error("NodeDataMsgHandler, _generate_disk_space_alert was NOT successful.")
            return

        # Changing disk_usage_threshold type according to what value type entered in config file
        self._disk_usage_threshold = str(self._disk_usage_threshold)
        try:
            if self._disk_usage_threshold.isdigit():
                self._disk_usage_threshold = int(self._disk_usage_threshold)
            else:
                self._disk_usage_threshold = float(self._disk_usage_threshold)
        except ValueError:
            logger.warning("Disk Space Alert, Invalid disk_usage_threshold value are entered in config.")
            # Assigning default value to _disk_usage_threshold
            self._disk_usage_threshold = self.DEFAULT_DISK_USAGE_THRESHOLD

        if self._node_sensor.disk_used_percentage >= self._disk_usage_threshold \
           and not self.high_usage['disk']:

            self.high_usage['disk'] = True
            # Create the disk space data message and hand it over
            # to the egress processor to transmit
            fault_event = "Disk usage has increased to {}%, "\
                "beyond the configured threshold of {}%.".format(
                    self._node_sensor.disk_used_percentage,
                    self._disk_usage_threshold
                )
            logger.warning(fault_event)
            diskSpaceAlertMsg = DiskSpaceAlertMsg(self._node_sensor.host_id,
                                    self._epoch_time,
                                    self._node_sensor.total_space,
                                    self._node_sensor.free_space,
                                    self._node_sensor.disk_used_percentage,
                                    self._units,
                                    self.FAULT,fault_event)

            # Add in uuid if it was present in the json request
            if self._uuid is not None:
                diskSpaceAlertMsg.set_uuid(self._uuid)
            jsonMsg = diskSpaceAlertMsg.getJson()
            self.disk_sensor_data = jsonMsg
            self.os_sensor_type["disk_space"] = self.disk_sensor_data

            # Transmit it to message processor
            self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)
            # Save the new state in Persistent Cache.
            self.persist_state_data('disk', 'DISK_USAGE_DATA')

        if self._node_sensor.disk_used_percentage <= self._disk_usage_threshold \
           and self.high_usage['disk']:

            # Create the disk space data message and hand it over
            # to the egress processor to transmit
            fault_resolved_event = "Disk usage has decreased to {}%, "\
                "lower than the configured threshold of {}%.".format(
                    self._node_sensor.disk_used_percentage,
                    self._disk_usage_threshold
                )
            logger.info(fault_resolved_event)
            diskSpaceAlertMsg = DiskSpaceAlertMsg(self._node_sensor.host_id,
                                    self._epoch_time,
                                    self._node_sensor.total_space,
                                    self._node_sensor.free_space,
                                    self._node_sensor.disk_used_percentage,
                                    self._units,
                                    self.FAULT_RESOLVED,
                                    fault_resolved_event
                                    )

            # Add in uuid if it was present in the json request
            if self._uuid is not None:
                diskSpaceAlertMsg.set_uuid(self._uuid)
            jsonMsg = diskSpaceAlertMsg.getJson()
            self.disk_sensor_data = jsonMsg
            self.os_sensor_type["disk_space"] = self.disk_sensor_data

            # Transmit it to message processor
            self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)
            self.high_usage['disk'] = False
            # Save the new state in Persistent Cache.
            self.persist_state_data('disk', 'DISK_USAGE_DATA')

    def _generate_raid_data(self, jsonMsg):
        """Create & transmit a RAID status data message as defined
            by the sensor response json schema"""
        successful = self._node_sensor.read_data("raid", self._get_debug(), self._units)
        if not successful:
            logger.error("NodeDataMsgHandler, updating RAID information was NOT successful.")
            return

        # See if status is in the msg; ie it's an internal msg from the RAID sensor
        if jsonMsg.get("sensor_request_type").get("node_data").get("status") is not None:
            sensor_request = jsonMsg.get("sensor_request_type").get("node_data")
            host_name = sensor_request.get("host_id")
            alert_type = sensor_request.get("alert_type")
            alert_id = sensor_request.get("alert_id")
            severity = sensor_request.get("severity")
            info = sensor_request.get("info")
            specific_info = sensor_request.get("specific_info")
            self._raid_device = jsonMsg.get("sensor_request_type").get("node_data").get("specific_info").get("device")
            self._raid_drives = list(jsonMsg.get("sensor_request_type").get("node_data").get("specific_info").get("drives"))
            raidDataMsg = RAIDdataMsg(host_name, alert_type, alert_id, severity, info, specific_info)
            # Add in uuid if it was present in the json request
            if self._uuid is not None:
                raidDataMsg.set_uuid(self._uuid)
            jsonMsg = raidDataMsg.getJson()
            self.raid_sensor_data = jsonMsg
            self.os_sensor_type["raid_data"] = self.raid_sensor_data

            # Loop thru each index of drives containing only paths and fill in with s/n
            for drive in self._raid_drives:
                self._log_debug("drive: %s" % str(drive))

                if drive.get("identity") is not None:
                    path = drive.get("identity").get("path")
                    self._log_debug("path: %s" % str(path))

                    # Lookup the serial number from the path
                    serial_number = str(self._drive_by_device_name.get(path))
                    self._log_debug("serial_number: %s" % str(serial_number))
                    if serial_number != "None":
                        drive["identity"]["serialNumber"] = serial_number

                    # Change device path to path-byid
                    drive_byid = str(self._drive_byid_by_serial_number.get(serial_number))
                    if drive_byid != "None":
                        drive["identity"]["path"] = drive_byid

            self._log_debug("_generate_raid_data, host_id: %s, device: %s, drives: %s" %
                    (self._node_sensor.host_id, self._raid_device, str(self._raid_drives)))

    def _generate_raid_integrity_data(self, jsonMsg):
        """Create & transmit a Validate RAID result data message as defined
            by the sensor response json schema"""
        logger.debug("NodeDataMsgHandler, Validating RAID information")

        # See if status is in the msg; ie it's an internal msg from the RAID sensor
        if jsonMsg.get("sensor_request_type").get("node_data").get("status") is not None:
            sensor_request = jsonMsg.get("sensor_request_type").get("node_data")
            host_name = sensor_request.get("host_id")
            alert_type = sensor_request.get("alert_type")
            alert_id = sensor_request.get("alert_id")
            severity = sensor_request.get("severity")
            info = sensor_request.get("info")
            specific_info = sensor_request.get("specific_info")
            self._alert = jsonMsg.get("sensor_request_type").get("node_data").get("specific_info").get("error")
            RAIDintegrityMsg = RAIDIntegrityMsg(host_name, alert_type, alert_id, severity, info, specific_info)
            # Add in uuid if it was present in the json request
            if self._uuid is not None:
                RAIDintegrityMsg.set_uuid(self._uuid)
            jsonMsg = RAIDintegrityMsg.getJson()
            self.raid_integrity_data = jsonMsg
            self.os_sensor_type["raid_integrity"] = self.raid_integrity_data

            self._log_debug("_generate_raid_integrity_data, host_id: %s" %
                    (self._node_sensor.host_id))

    def _generate_node_fru_data(self, jsonMsg):
        """Create & transmit a FRU IPMI data message as defined
            by the sensor response json schema"""

        if self._node_sensor.host_id is None:
            successful = self._node_sensor.read_data("None", self._get_debug(), self._units)
            if not successful:
                logger.error("NodeDataMsgHandler, updating host information was NOT successful.")

        if jsonMsg.get("sensor_request_type").get("node_data") is not None:
            self._fru_info = jsonMsg.get("sensor_request_type").get("node_data")
            node_ipmi_data_msg = NodeIPMIDataMsg(self._fru_info)

        if self._uuid is not None:
            node_ipmi_data_msg.set_uuid(self._uuid)
        jsonMsg = node_ipmi_data_msg.getJson()
        self._write_internal_msgQ(EgressProcessor.name(), jsonMsg)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(NodeDataMsgHandler, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(NodeDataMsgHandler, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(NodeDataMsgHandler, self).shutdown()
