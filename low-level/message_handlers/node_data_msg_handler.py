"""
 ****************************************************************************
 Filename:          node_data_msg_handler.py
 Description:       Message Handler for requesting node data
 Creation Date:     06/18/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import time

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import enabled_products, COMMON_CONFIGS

from json_msgs.messages.sensors.host_update import HostUpdateMsg
from json_msgs.messages.sensors.local_mount_data import LocalMountDataMsg
from json_msgs.messages.sensors.cpu_data import CPUdataMsg
from json_msgs.messages.sensors.if_data import IFdataMsg
from json_msgs.messages.sensors.raid_data import RAIDdataMsg
from json_msgs.messages.sensors.disk_space_alert import DiskSpaceAlertMsg
from json_msgs.messages.sensors.node_hw_data import NodeIPMIDataMsg

from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

from message_handlers.logging_msg_handler import LoggingMsgHandler

class NodeDataMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for generic node requests and generating
        host update messages on a regular interval"""

    MODULE_NAME = "NodeDataMsgHandler"
    PRIORITY    = 2

    # Section and keys in configuration file
    NODEDATAMSGHANDLER = MODULE_NAME.upper()
    TRANSMIT_INTERVAL = 'transmit_interval'
    UNITS = 'units'
    DISK_USAGE_THRESHOLD = 'disk_usage_threshold'
    DEFAULT_DISK_USAGE_THRESHOLD = 80
    CPU_USAGE_THRESHOLD = 'cpu_usage_threshold'
    DEFAULT_CPU_USAGE_THRESHOLD = 80
    HOST_MEMORY_USAGE_THRESHOLD = 'host_memory_usage_threshold'
    DEFAULT_HOST_MEMORY_USAGE_THRESHOLD = 80

    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "site_id"
    CLUSTER_ID = "cluster_id"
    NODE_ID = "node_id"
    RACK_ID = "rack_id"

    IPMI_RESOURCE_TYPE_PSU = "node:fru:psu"
    IPMI_RESOURCE_TYPE_FAN = "node:fru:fan"
    IPMI_RESOURCE_TYPE_DISK = "node:fru:disk"
    NW_RESOURCE_TYPE = "node:interface:nw"
    NW_CABLE_RESOURCE_TYPE = "node:interface:nw:cable"
    host_fault = False
    cpu_fault = False
    disk_fault = False
    if_fault = False
    FAULT = "fault"
    FAULT_RESOLVED = "fault_resolved"
    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RabbitMQegressProcessor"],
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

        self._transmit_interval = int(self._conf_reader._get_value_with_default(
                                                self.NODEDATAMSGHANDLER,
                                                self.TRANSMIT_INTERVAL,
                                                60))
        self._units = self._conf_reader._get_value_with_default(
                                                self.NODEDATAMSGHANDLER,
                                                self.UNITS,
                                                "MB")
        self._disk_usage_threshold = self._conf_reader._get_value_with_default(
                                                self.NODEDATAMSGHANDLER,
                                                self.DISK_USAGE_THRESHOLD,
                                                self.DEFAULT_DISK_USAGE_THRESHOLD)

        self._cpu_usage_threshold = self._conf_reader._get_value_with_default(
                                                self.NODEDATAMSGHANDLER,
                                                self.CPU_USAGE_THRESHOLD,
                                                self.DEFAULT_CPU_USAGE_THRESHOLD)

        self._host_memory_usage_threshold = self._conf_reader._get_value_with_default(
                                                self.NODEDATAMSGHANDLER,
                                                self.HOST_MEMORY_USAGE_THRESHOLD,
                                                self.DEFAULT_HOST_MEMORY_USAGE_THRESHOLD)

        self.site_id = self._conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.SITE_ID),
                                                '001')
        self.rack_id = self._conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.RACK_ID),
                                                '001')
        self.node_id = self._conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.NODE_ID),
                                                '001')

        self.cluster_id = self._conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.CLUSTER_ID,
                                                '0')
        self.prev_nw_status = {}
        self.bmcNwStatus = None
        self.prev_cable_cnxns = {}
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
            "system" : self.host_sensor_data,
            "nw"   : self.if_sensor_data,
            "cpu"  : self.cpu_sensor_data,
            "raid_data" : self.raid_sensor_data
        }

        # UUID used in json msgs
        self._uuid = None

        # Dict of drives by device name from systemd
        self._drive_by_device_name = {}

        # Dict of drive path by-ids by serial number from systemd
        self._drive_byid_by_serial_number = {}

        self._import_products(product)

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

            if self.sensor_type == "system":
                self._generate_host_update()
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(),
                                          sensor_message_type)
                else:
                    self._log_debug(f"NodeDataMsgHandler, _process_msg, \
                        No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "cpu":
                self._generate_cpu_data()
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(),
                                          sensor_message_type)
                else:
                    self._log_debug(f"NodeDataMsgHandler, _process_msg, \
                        No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "nw":
                self._generate_if_data()
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(),
                                          sensor_message_type)
                else:
                    self._log_debug(f"NodeDataMsgHandler, _process_msg, \
                        No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "disk_space":
                self._generate_disk_space_alert()
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(),
                                          sensor_message_type)
                else:
                    self._log_debug(f"NodeDataMsgHandler, _process_msg, \
                        No past data found for {self.sensor_type} sensor type")

            elif self.sensor_type == "raid_data":
                self._generate_raid_data(jsonMsg)
                sensor_message_type = self.os_sensor_type.get(self.sensor_type, "")
                if sensor_message_type:
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(),
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
            # Assigning default value to _disk_usage_threshold
            self._host_memory_usage_threshold = self.DEFAULT_HOST_MEMORY_USAGE_THRESHOLD
        if self._node_sensor.total_memory["percent"] >= self._host_memory_usage_threshold:
            # Create the disk space data message and hand it over to the egress processor to transmit
            if not self.host_fault:
                self.host_fault = True
                # Create the disk space data message and hand it over to the egress processor to transmit
                logger.warning("Host Memory usage increased to {}%, beyond configured threshold of {}%".\
                    format(self._node_sensor.total_memory["percent"], self._host_memory_usage_threshold))

                logged_in_users = []
                # Create the host update message and hand it over to the egress processor to transmit
                hostUpdateMsg = HostUpdateMsg(self._node_sensor.host_id,
                                        self._epoch_time,
                                        self._node_sensor.boot_time,
                                        self._node_sensor.up_time,
                                        self._node_sensor.uname, self._units,
                                        self.site_id, self.rack_id,
                                        self.node_id, self.cluster_id,
                                        self._node_sensor.total_memory,
                                        self._node_sensor.logged_in_users,
                                        self._node_sensor.process_count,
                                        self._node_sensor.running_process_count,
                                        self.FAULT
                                        )
                # Add in uuid if it was present in the json request
                if self._uuid is not None:
                    hostUpdateMsg.set_uuid(self._uuid)
                jsonMsg = hostUpdateMsg.getJson()
                # Transmit it out over rabbitMQ channel
                self.host_sensor_data = jsonMsg
                self.os_sensor_type["system"] = self.host_sensor_data
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

        if (self._node_sensor.total_memory["percent"] < self._host_memory_usage_threshold) and (self.host_fault == True):
                logger.warning("Host Memory usage decrease to {}%, lesser than configured threshold of {}%".\
                    format(self._host_memory_usage_threshold, self._node_sensor.total_memory["percent"]))
                logged_in_users = []
                # Create the host update message and hand it over to the egress processor to transmit
                hostUpdateMsg = HostUpdateMsg(self._node_sensor.host_id,
                                        self._epoch_time,
                                        self._node_sensor.boot_time,
                                        self._node_sensor.up_time,
                                        self._node_sensor.uname, self._units,
                                        self.site_id, self.rack_id,
                                        self.node_id, self.cluster_id,
                                        self._node_sensor.total_memory,
                                        self._node_sensor.logged_in_users,
                                        self._node_sensor.process_count,
                                        self._node_sensor.running_process_count,
                                        self.FAULT_RESOLVED
                                        )

                # Add in uuid if it was present in the json request
                if self._uuid is not None:
                    hostUpdateMsg.set_uuid(self._uuid)
                jsonMsg = hostUpdateMsg.getJson()
                # Transmit it out over rabbitMQ channel
                self.host_sensor_data = jsonMsg
                self.os_sensor_type["system"] = self.host_sensor_data
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)
                self.host_fault = False

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

        # Transmit it out over rabbitMQ channel
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

    def _generate_cpu_data(self):
        """Create & transmit a cpu_data message as defined
            by the sensor response json schema"""

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

        if self._node_sensor.cpu_usage >= self._cpu_usage_threshold:

            if not self.cpu_fault :
                self.cpu_fault = True
                # Create the cpu usage data message and hand it over to the egress processor to transmit
                logger.warning("CPU usage increased to {}%, beyond configured threshold of {}%".\
                    format(self._node_sensor.cpu_usage, self._cpu_usage_threshold))

                # Create the local mount data message and hand it over to the egress processor to transmit
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
                                    self.site_id,
                                    self.rack_id,
                                    self.node_id,
                                    self.cluster_id,
                                    self.FAULT
                                )

                # Add in uuid if it was present in the json request
                if self._uuid is not None:
                    cpuDataMsg.set_uuid(self._uuid)
                jsonMsg = cpuDataMsg.getJson()
                self.cpu_sensor_data = jsonMsg
                self.os_sensor_type["cpu"] = self.cpu_sensor_data
                # Transmit it out over rabbitMQ channel
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

        if (self._node_sensor.cpu_usage <= self._cpu_usage_threshold) and (self.cpu_fault == True):
            # Create the cpu usage data message and hand it over to the egress processor to transmit
            logger.warning("CPU usage decrised to {}%, lesser than configured threshold of {}%".\
                format(self._cpu_usage_threshold, self._node_sensor.cpu_usage))

            # Create the local mount data message and hand it over to the egress processor to transmit
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
                                self.site_id,
                                self.rack_id,
                                self.node_id,
                                self.cluster_id,
                                self.FAULT_RESOLVED
                            )

            # Add in uuid if it was present in the json request
            if self._uuid is not None:
                cpuDataMsg.set_uuid(self._uuid)
            jsonMsg = cpuDataMsg.getJson()
            self.cpu_sensor_data = jsonMsg
            self.os_sensor_type["cpu"] = self.cpu_sensor_data
            # Transmit it out over rabbitMQ channel
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)
            self.cpu_fault = False

    def _send_ifdata_json_msg(self, sensor_type, msg_sensor):
        """A resuable method for transmitting IFDataMsg to RMQ and IEM logging"""
        # Add in uuid if it was present in the json request
        if self._uuid is not None:
            msg_sensor.set_uuid(self._uuid)
        jsonMsg = msg_sensor.getJson()
        self.if_sensor_data = jsonMsg
        self.os_sensor_type[sensor_type] = self.if_sensor_data

        # Send the event to logging msg handler to send IEM message to journald
        #internal_json_msg=json.dumps({
        #                        'actuator_request_type': {
        #                            'logging': {
        #                                'log_level': 'LOG_WARNING',
        #                                'log_type': 'IEM',
        #                                'log_msg': '{}'.format(jsonMsg)}}})
        #self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

        # Transmit it out over rabbitMQ channel
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

    def _generate_if_data(self):
        """Create & transmit a network interface data message as defined
            by the sensor response json schema"""

        # Notify the node sensor to update its data required for the if_data message
        successful = self._node_sensor.read_data("if_data", self._get_debug())
        if not successful:
            logger.error("NodeDataMsgHandler, _generate_if_data was NOT successful.")
        interfaces = self._node_sensor.if_data
        nw_alerts = self._get_nwalert(interfaces)
        for nw_resource_id, nw_state in nw_alerts.items():
            ifDataMsg = IFdataMsg(self._node_sensor.host_id,
                            self._node_sensor.local_time,
                            self._node_sensor.if_data,
                            nw_resource_id,
                            self.NW_RESOURCE_TYPE,
                            self.site_id, self.node_id, self.cluster_id, self.rack_id, nw_state)
            self._send_ifdata_json_msg("nw", ifDataMsg)

        # Get all cable connections state and generate alert on
        # cables identified for fault detected and resolved state
        nw_cable_alerts = self._nw_cable_alert_exists(interfaces)

        for nw_cable_resource_id, state in nw_cable_alerts.items():
            ifDataMsg = IFdataMsg(self._node_sensor.host_id,
                            self._node_sensor.local_time,
                            self._node_sensor.if_data,
                            nw_cable_resource_id,
                            self.NW_CABLE_RESOURCE_TYPE,
                            self.site_id, self.node_id, self.cluster_id, self.rack_id, state)
            self._send_ifdata_json_msg("nw", ifDataMsg)

    def _get_nwalert(self, interfaces):
        """
        Get network interfaces with fault/OK state for each interface.
        Parameters:
                    interfaces(list) : List of availabel network interfaces

        Returns: Dictionary of network interfaces having key as interface name and value as fault state.

        Return type: dict
        """
        nw_alerts = {}
        try:
            for interface in interfaces:
                interface_name = interface.get("ifId")
                nw_status = interface.get("nwStatus")
                # fault detected (Down/UNKNOWN, Up/UNKNOWN to Down, Up/Down to UNKNOWN)
                if nw_status == 'DOWN' or nw_status == 'UNKNOWN':
                    if self.prev_nw_status.get(interface_name) != nw_status:
                        if self.prev_nw_status.get(interface_name) and self.prev_nw_status.get(interface_name) == 'UP':
                            logger.warning(f"Network connection fault is detected for interface:'{interface_name}'")
                            nw_alerts[interface_name] = self.FAULT
                        self.prev_nw_status[interface_name] = nw_status
                # fault resolved (Down to Up)
                elif nw_status == 'UP':
                    if self.prev_nw_status.get(interface_name) != nw_status:
                        if self.prev_nw_status.get(interface_name):
                            logger.info(f"Network connection fault is resolved for interface:'{interface_name}'")
                            nw_alerts[interface_name] = self.FAULT_RESOLVED
                        self.prev_nw_status[interface_name] = nw_status
                else:
                    logger.warning(f"Network connection state is:'{nw_status}', for interface:'{interface_name}'")
        except Exception as e:
            logger.error(f"Exception occurs while checking for network alert condition:'{e}'")
        return nw_alerts

    def _nw_cable_alert_exists(self, interfaces):
        """Checks cable connection status with physical link(carrier) state and
        avoids duplicate alert reporting by comparing with its previous state.
        Fault detection is identified by physical link state Down.
        Fault resolved is identified by physical link state changed from Down to Up.
        """
        identified_cables = {}

        for interface in interfaces:

            interface_name = interface.get("ifId")
            phy_link_status = interface.get("nwCableConnStatus")

            # fault detected (Down, Up to Down)
            if phy_link_status == 'DOWN':
                if self.prev_cable_cnxns.get(interface_name) != phy_link_status:
                    if self.prev_cable_cnxns.get(interface_name):
                        logger.warning(f"Cable connection fault is detected with '{interface_name}'")
                        identified_cables[interface_name] = self.FAULT
                    self.prev_cable_cnxns[interface_name] = phy_link_status
            # fault resolved (Down to Up)
            elif phy_link_status == 'UP':
                if self.prev_cable_cnxns.get(interface_name) != phy_link_status:
                    if self.prev_cable_cnxns.get(interface_name):
                        logger.info(f"Cable connection fault is resolved with '{interface_name}'")
                        identified_cables[interface_name] = self.FAULT_RESOLVED
                    self.prev_cable_cnxns[interface_name] = phy_link_status
            else:
                logger.warning(f"Cable connection state is unknown with '{interface_name}'")

        return identified_cables

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

        if self._node_sensor.disk_used_percentage >= self._disk_usage_threshold:
            if not self.disk_fault:
                self.disk_fault = True
                # Create the disk space data message and hand it over to the egress processor to transmit
                logger.warning("Disk usage increased to {}%, beyond configured threshold of {}%".\
                    format(self._node_sensor.disk_used_percentage, self._disk_usage_threshold))
                diskSpaceAlertMsg = DiskSpaceAlertMsg(self._node_sensor.host_id,
                                        self._epoch_time,
                                        self._node_sensor.total_space,
                                        self._node_sensor.free_space,
                                        self._node_sensor.disk_used_percentage,
                                        self._units,
                                        self.site_id, self.rack_id,
                                        self.node_id, self.cluster_id, self.FAULT)

                # Add in uuid if it was present in the json request
                if self._uuid is not None:
                    diskSpaceAlertMsg.set_uuid(self._uuid)
                jsonMsg = diskSpaceAlertMsg.getJson()
                self.disk_sensor_data = jsonMsg
                self.os_sensor_type["disk_space"] = self.disk_sensor_data
                # Transmit it out over rabbitMQ channel
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

        if (self._node_sensor.disk_used_percentage <= self._disk_usage_threshold) and (self.disk_fault == True):
            # Create the disk space data message and hand it over to the egress processor to transmit
            logger.warning("Disk usage decrised to {}%, lesser than threshold of {}%".\
                format(self._disk_usage_threshold, self._node_sensor.disk_used_percentage, ))
            diskSpaceAlertMsg = DiskSpaceAlertMsg(self._node_sensor.host_id,
                                    self._epoch_time,
                                    self._node_sensor.total_space,
                                    self._node_sensor.free_space,
                                    self._node_sensor.disk_used_percentage,
                                    self._units,
                                    self.site_id,
                                    self.rack_id,
                                    self.node_id,
                                    self.cluster_id,
                                    self.FAULT_RESOLVED
                                    )

            # Add in uuid if it was present in the json request
            if self._uuid is not None:
                diskSpaceAlertMsg.set_uuid(self._uuid)
            jsonMsg = diskSpaceAlertMsg.getJson()
            self.disk_sensor_data = jsonMsg
            self.os_sensor_type["disk_space"] = self.disk_sensor_data
            # Transmit it out over rabbitMQ channel
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)
            self.disk_fault = False

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

        self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

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

