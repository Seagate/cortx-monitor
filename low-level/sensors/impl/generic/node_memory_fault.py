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

"""
Sensor Module Thread responsible for sensing RAM memory faults on the Node server

"""

import json
import socket
import time
import uuid
import os

from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from message_handlers.logging_msg_handler import LoggingMsgHandler
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from framework.base.module_thread import SensorThread
from framework.utils.severity_reader import SeverityReader
from framework.utils.procfs_interface import ProcFS
from framework.utils.tool_factory import ToolFactory
from framework.utils.utility import Utility
from framework.utils.store_factory import file_store
from framework.base.sspl_constants import COMMON_CONFIGS, DATA_PATH

# Override default store
store = file_store

class MemFaultSensor(SensorThread, InternalMsgQ):
    """Memory fault Sensor which runs on its own thread once every power cycle and
       is responsible for identifying total RAM memory on the node and any errors in it using
       available tool/utility"""

    SENSOR_NAME = "MemFaultSensor"
    PRIORITY = 1
    RESOURCE_TYPE = "node:os:memory"

    # section in the configuration store
    SYSTEM_INFORMATION_KEY = "SYSTEM_INFORMATION"
    SITE_ID_KEY = "site_id"
    CLUSTER_ID_KEY = "cluster_id"
    NODE_ID_KEY = "node_id"
    RACK_ID_KEY = "rack_id"
    POLLING_INTERVAL_KEY = "polling_interval"
    CACHE_DIR_NAME  = "server"


    RESOURCE_ID = "0"
    DEFAULT_POLLING_INTERVAL = '0'

    PROBE = "probe"

    # Dependency list
    DEPENDENCIES = {
	       "plugins": ["NodeDataMsgHandler", "LoggingMsgHandler"],
        "rpms": []

        }

    @staticmethod
    def name():
        """@return: name of the module."""
        return MemFaultSensor.SENSOR_NAME

    def __init__(self, utility_instance=None):
        """init method"""
        super(MemFaultSensor, self).__init__(self.SENSOR_NAME, self.PRIORITY)

        # Initialize the utility instance
        self._utility_instance = utility_instance
        self.total_mem = None
        self.mem_path_file = None
        self.prev_mem = None
        self.fault_alert_state = "Neutral State"
        # Flag to indicate suspension of module
        self._suspended = False


    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(MemFaultSensor, self).initialize(conf_reader)

        super(MemFaultSensor, self).initialize_msgQ(msgQlist)

        self._site_id = self._conf_reader._get_value_with_default(
            self.SYSTEM_INFORMATION_KEY,
            COMMON_CONFIGS.get(self.SYSTEM_INFORMATION_KEY).get(self.SITE_ID_KEY), '001')
        self._cluster_id = self._conf_reader._get_value_with_default(
            self.SYSTEM_INFORMATION_KEY,
            COMMON_CONFIGS.get(self.SYSTEM_INFORMATION_KEY).get(self.CLUSTER_ID_KEY), '001')
        self._rack_id = self._conf_reader._get_value_with_default(
            self.SYSTEM_INFORMATION_KEY,
            COMMON_CONFIGS.get(self.SYSTEM_INFORMATION_KEY).get(self.RACK_ID_KEY), '001')
        self._node_id = self._conf_reader._get_value_with_default(
            self.SYSTEM_INFORMATION_KEY,
            COMMON_CONFIGS.get(self.SYSTEM_INFORMATION_KEY).get(self.NODE_ID_KEY), '001')

        # get the mem fault implementor from configuration
        mem_fault_utility = self._conf_reader._get_value_with_default(
            self.name().capitalize(), self.PROBE,
            "procfs")

        self.polling_interval = int(self._conf_reader._get_value_with_default(
            self.SENSOR_NAME.upper(), self.POLLING_INTERVAL_KEY, self.DEFAULT_POLLING_INTERVAL))

        # Creating the instance of ToolFactory class
        self.tool_factory = ToolFactory()

        # Creating the instance of Utility class
        self.utility = Utility()

        try:
            # Get the instance of the utility using ToolFactory
            self._utility_instance = self._utility_instance or \
                                self.tool_factory.get_instance(mem_fault_utility)
#            self._utility_instance.initialize()
        except KeyError as key_error:
            logger.error(
                "Unable to get the instance of {} \
                Utility. Hence shutting down the sensor {}"\
                .format(mem_fault_utility, MemFaultSensor.SENSOR_NAME))
            self.shutdown()

        if self.utility.is_env_vm():
            self.shutdown()

        cache_dir_path = os.path.join(DATA_PATH, self.CACHE_DIR_NAME)
        self.MEM_FAULT_SENSOR_DATA = os.path.join(cache_dir_path, f'MEM_FAULT_SENSOR_DATA_{self._node_id}')

        return True

    def get_stored_mem_info(self):
        """ Get the memory info from consul"""

        if store.exists(self.MEM_FAULT_SENSOR_DATA):
            consul_data = (store.get(self.MEM_FAULT_SENSOR_DATA)).split(":")
            self.prev_mem = consul_data[0].strip()
            self.fault_alert_state = consul_data[1].strip()
        
    def put_mem_info(self, total_memory_size):
        """ Store the current memory in Consul"""

        store.put(f"{total_memory_size}:{self.fault_alert_state}", self.MEM_FAULT_SENSOR_DATA)

    def run(self):
        """Run the sensor on its own thread"""

        alert_type = "fault"

        mem_path = self._utility_instance.get_proc_memory('meminfo')
        if mem_path.is_file():
            self.mem_path_file = mem_path.read_text()
            mem_info_fields = self.mem_path_file.split()

            if mem_info_fields[0] == 'MemTotal:':
                self.total_mem = mem_info_fields[1]

                # Get data from store if available and compare to the current value
                self.get_stored_mem_info()

                if self.prev_mem is not None:
                    # Fault and Fault_resolved Both conditions are handled.
                    if int(self.prev_mem) > int(self.total_mem):
                        # update the store with new value, raise an alert of type "fault"
                        if self.fault_alert_state == "Neutral State":
                            self.fault_alert_state = "Fault Generated"
                            self._generate_alert(alert_type)
                            self.put_mem_info(self.prev_mem)

                    elif (int(self.prev_mem) <= int(self.total_mem)) and (self.fault_alert_state == "Fault Generated"):
                        self.fault_alert_state = "Neutral State"
                        alert_type = "fault_resolved"
                        self._generate_alert(alert_type)
                        self.put_mem_info(self.total_mem)
                else:
                    self.put_mem_info(self.total_mem)
            else:
                logger.error("MemFaultSensor: invalid file, shutting down the sensor")
                self.shutdown()
                return True
        else:
            logger.error("MemFaultSensor: file does not exist, shutting down the sensor")
            self.shutdown()
            return True

        # Do not proceed if module is suspended
        # Memory sensor is going to trigger only during SSPL reboot; at reboot time a sensor
        # can not be in suspended state.
        # Commented code is retained if in future we want to make the sensor periodic,
        # this piece will be needed
        #if self._suspended is True:
        #    self._scheduler.enter(self.polling_interval, self._priority, self.run, ())
        #    return

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()


        # self scheduling is commented so that the process runs only once per SSPL reboot
        # Enable with correct polling_interval if in future memory sensor needs to run periodically
        #self._scheduler.enter(self.polling_interval, self._priority, self.run, ())

    def _create_json_message(self, alert_type):
        """Creates a defined json message structure which can flow inside SSPL
           modules"""

        internal_json_msg = None
        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        host_name = socket.gethostname()

        specific_info = {}
        specific_info_list = []
        if alert_type == "fault":
            specific_info["event"] = \
                    "Total available main memory value decreased from {} kB to {} kB"\
                    .format(self.prev_mem, self.total_mem)
        elif alert_type == "fault_resolved":
            specific_info["event"] = \
                    "Total main memory value available {} kB"\
                    .format(self.total_mem)

        # populate all the data from /proc/meminfo
        split_strs = [s.split(maxsplit=1) for s in self.mem_path_file.splitlines()]
        dictionary_str = dict(split_strs)
        specific_info["meminfo"] = dictionary_str
        specific_info_list.append(specific_info)

        alert_specific_info = specific_info_list

        info = {
            "site_id": self._site_id,
            "cluster_id": self._cluster_id,
            "rack_id": self._rack_id,
            "node_id": self._node_id,
            "resource_type": self.RESOURCE_TYPE,
            "resource_id": self.RESOURCE_ID,
            "event_time": epoch_time
            }

        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                "node_data": {
                    "status": "update",
                    "host_id": host_name,
                    "alert_type": alert_type,
                    "severity": severity,
                    "alert_id": alert_id,
                    "info": info,
                    "specific_info": alert_specific_info
                    }
            }})

        return internal_json_msg


    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
           epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

    def _generate_alert(self, alert_type):
        """Queues the message to NodeData Message Handler"""

        json_msg = self._create_json_message(alert_type)
        if json_msg:
            self._write_internal_msgQ(NodeDataMsgHandler.name(), json_msg)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(MemFaultSensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(MemFaultSensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(MemFaultSensor, self).shutdown()
