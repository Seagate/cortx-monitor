"""
Sensor Module Thread responsible for reporting CPU faults
on the Node server
"""

import json
import socket
import time
import uuid

from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from message_handlers.logging_msg_handler import LoggingMsgHandler
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from framework.base.module_thread import SensorThread
from framework.utils.severity_reader import SeverityReader
from framework.utils.sysfs_interface import SysFS
from framework.utils.store_factory import store
from framework.utils.tool_factory import ToolFactory
from framework.base.sspl_constants import COMMON_CONFIGS

class CPUFaultSensor(SensorThread, InternalMsgQ):
    """CPU Fault Sensor which runs on its own thread on each boot up and
       is responsible for sensing changes in online CPUs using
       available tool/utility"""

    SENSOR_NAME = "CPUFaultSensor"
    PRIORITY = 1
    RESOURCE_TYPE = "node:os:cpu:core"

    # Section in the configuration store
    SYSTEM_INFORMATION_KEY = "SYSTEM_INFORMATION"
    SITE_ID_KEY = "site_id"
    CLUSTER_ID_KEY = "cluster_id"
    NODE_ID_KEY = "node_id"
    RACK_ID_KEY = "rack_id"

    RESOURCE_ID = "CPU-"

    PROBE = "probe"

    # Dependency list
    DEPENDENCIES = {
            "plugins": ["NodeDataMsgHandler", "LoggingMsgHandler"],
            "rpms": []

        }

    @staticmethod
    def name():
        """@return: name of the module."""
        return CPUFaultSensor.SENSOR_NAME

    def __init__(self, utility_instance=None):
        """init method"""
        super(CPUFaultSensor, self).__init__(self.SENSOR_NAME,
                                             self.PRIORITY)

        # Initialize the utility instance
        self._utility_instance = utility_instance

        # CPU info
        self.stored_cpu_info = None
        self.prev_cpu_info = None
        self.current_cpu_info = None

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(CPUFaultSensor, self).initialize(conf_reader)

        super(CPUFaultSensor, self).initialize_msgQ(msgQlist)

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

        # get the cpu fault implementor from configuration
        cpu_fault_utility = self._conf_reader._get_value_with_default(
                                    self.name().capitalize(), self.PROBE,
                                    'sysfs')

        # Creating the instance of ToolFactory class
        self.tool_factory = ToolFactory()

        try:
            # Get the instance of the utility using ToolFactory
            self._utility_instance = self._utility_instance or \
                                self.tool_factory.get_instance(cpu_fault_utility)
        except Exception as e:
            logger.error(f"Error while initializing, shutting down CPUFaultSensor : {e}")
            self.shutdown()

        return True

    def read_stored_cpu_info(self):
        """Read the most recent stored cpu info"""
        try:
            if self.stored_cpu_info is None:
                self.stored_cpu_info = store.get('CPU_FAULT_SENSOR_DATA')
            if self.stored_cpu_info is not None and self._node_id in self.stored_cpu_info.keys():
                self.prev_cpu_info = self.stored_cpu_info[self._node_id]['CPU_LIST']
        except Exception as e:
            logger.error(f"Error while reading stored cpu info, shutting down CPUFaultSensor : {e}")
            self.shutdown()

    def read_current_cpu_info(self):
        """Read current cpu info"""
        try:
            self.current_cpu_info = self._utility_instance.get_cpu_info()
        except Exception as e:
            logger.error(f"Error while reading current cpu info, shutting down CPUFaultSensor : {e}")
            self.shutdown()

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()
        # Read recent stored cpu info
        self.read_stored_cpu_info()
        # Store alerts to be sent here
        self.alerts_for = {}
        # Specific info field for alerts
        self.specific_info = []
        # Read current cpu info
        self.read_current_cpu_info()

        to_update = False
        # Compare with previous cpu info
        # If a cpu is present in prev_cpu_info and not present in current_cpu_info : fault alert is generated
        # If a cpu is present in current_cpu_info and not present in prev_cpu_info : two possibilities
        #   1) if cpu has an outstanding fault alert : it is a repaired cpu, hence generate fault_resolved
        #   2) if cpu has no outstanding alert : it is a newly added cpu, do not do anything
        try:
            if self.prev_cpu_info:
                if self.current_cpu_info != self.prev_cpu_info:
                    # Create a set of all relevant cpus
                    cpu_list = set(self.prev_cpu_info + self.current_cpu_info)
                    # Iterate through the set
                    for cpu in cpu_list:
                        if cpu not in self.current_cpu_info and cpu not in self.stored_cpu_info[self._node_id]['FAULT_LIST']:
                            # This is a failed cpu
                            self.stored_cpu_info[self._node_id]['FAULT_LIST'].append(cpu)
                            self.alerts_for[cpu] = "fault"
                        elif cpu not in self.prev_cpu_info and cpu in self.stored_cpu_info[self._node_id]['FAULT_LIST']:
                            # This is a repaired cpu
                            self.alerts_for[cpu] = "fault_resolved"
                    # Update stored cpu info for next run
                    self.stored_cpu_info[self._node_id]['CPU_LIST'] = self.current_cpu_info
                    to_update = True
            else:
                # Previous cpu info not available, need to store current info
                if not self.stored_cpu_info:
                    # No info is available
                    self.stored_cpu_info = {}
                # Add info for the current node
                self.stored_cpu_info[self._node_id] = {}
                self.stored_cpu_info[self._node_id]['CPU_LIST'] = self.current_cpu_info
                self.stored_cpu_info[self._node_id]['FAULT_LIST'] = []
                # Update stored cpu info
                to_update = True

        except Exception as e:
            logger.error(f"Error while processing cpu info, shutting down CPUFaultSensor : {e}")
            self.shutdown()

        # Send alerts
        for cpu, alert_type in self.alerts_for.items():
            if self._generate_alert(cpu, alert_type) == True and alert_type == "fault_resolved":
                # Delete from the FAULT_LIST
                self.stored_cpu_info[self._node_id]['FAULT_LIST'].remove(cpu)

        # Update stored cpu info
        if to_update:
            store.put(self.stored_cpu_info, 'CPU_FAULT_SENSOR_DATA')

    def fill_specific_info(self):
        """Fills the specific info to be sent via alert"""
        if not self.specific_info:
            # Create a set of all relevant cpus
            cpu_list = set(self.prev_cpu_info + self.current_cpu_info)
            # Iterate through the set
            for cpu in cpu_list:
                item = {}
                item['resource_id'] = self.RESOURCE_ID + str(cpu)
                # Keep default state online
                item['state'] = "online"
                if cpu in self.alerts_for.keys():
                    if self.alerts_for[cpu] == "fault":
                        item['state'] = "offline"
                self.specific_info.append(item)

    def _create_json_message(self, cpu, alert_type):
        """Creates a defined json message structure which can flow inside SSPL
           modules"""

        internal_json_msg = None
        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        host_name = socket.gethostname()

        # Populate specific info
        self.fill_specific_info()
        alert_specific_info = self.specific_info

        info = {
                "site_id": self._site_id,
                "cluster_id": self._cluster_id,
                "rack_id": self._rack_id,
                "node_id": self._node_id,
                "resource_type": self.RESOURCE_TYPE,
                "resource_id": self.RESOURCE_ID + str(cpu),
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

    def _generate_alert(self, cpu, alert_type):
        """Queues the message to NodeData Message Handler"""
        try:
            json_msg = self._create_json_message(cpu, alert_type)
            if json_msg:
                self._write_internal_msgQ(NodeDataMsgHandler.name(), json_msg)
            return True
        except Exception as e:
            logger.error(f"Exception while sending alert : {e}")
            return False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(CPUFaultSensor, self).shutdown()
