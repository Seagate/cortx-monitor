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
  Description:       Message Handler for controlling the node
 ****************************************************************************
"""

import errno
import json
import socket

# Import Actuator states table
from framework.actuator_state_manager import actuator_state_manager
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.base.sspl_constants import enabled_products
from framework.utils.conf_utils import GLOBAL_CONF, RELEASE, SSPL_CONF, Conf
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.ack_response import AckResponseMsg
from json_msgs.messages.actuators.ndhw_ack_response import NodeHwAckResponseMsg
from message_handlers.disk_msg_handler import DiskMsgHandler
from message_handlers.service_msg_handler import ServiceMsgHandler
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor


class NodeControllerMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for controlling the node"""

    MODULE_NAME = "NodeControllerMsgHandler"
    PRIORITY    = 2

    SYS_INFORMATION = 'SYSTEM_INFORMATION'
    SETUP = 'setup'
    NODE_HW_ACTUATOR = 'NODEHWACTUATOR'
    IPMI_IMPLEMENTOR = 'ipmi_client'

    UNSUPPORTED_REQUEST = "Unsupported Request"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": [
                        "ServiceMsgHandler",
                        "RabbitMQegressProcessor",
                        "DiskMsgHandler"
                    ],
                    "rpms": []
    }

    @staticmethod
    def name():
        """ @return: name of the module."""
        return NodeControllerMsgHandler.MODULE_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return NodeControllerMsgHandler.DEPENDENCIES

    def __init__(self):
        super(NodeControllerMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        # Flag to indicate suspension of module
        self._suspended = False

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(NodeControllerMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(NodeControllerMsgHandler, self).initialize_msgQ(msgQlist)

        # Find a meaningful hostname to be used
        self.host_id = socket.getfqdn()
        self._HPI_actuator          = None
        self._GEM_actuator          = None
        self._PDU_actuator          = None
        self._RAID_actuator         = None
        self._IPMI_actuator         = None
        self._hdparm_actuator       = None
        self._smartctl_actuator     = None
        self._command_line_actuator = None
        self._NodeHW_actuator       = None

        self._import_products(product)
        self.setup = Conf.get(GLOBAL_CONF, f"{RELEASE}>{self.SETUP}","ssu")
        self.ipmi_client_name = None

    def _import_products(self, product):
        """Import classes based on which product is being used"""
        if product.lower() in [x.lower() for x in enabled_products]:
            from zope.component import queryUtility
            self._queryUtility = queryUtility

    def run(self):
        """Run the module periodically on its own thread."""
        self._set_debug(True)
        self._set_debug_persist(True)
        self._log_debug("Start accepting requests")

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(10, self._priority, self.run, ())
            return

        try:
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
            logger.exception(f"NodeControllerMsgHandler restarting: {ae}")

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and handles appropriately"""
        self._log_debug(f"_process_msg, jsonMsg: {jsonMsg}")

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        # Parse out the uuid so that it can be sent back in Ack message
        uuid = None
        if jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            self._log_debug(f"_processMsg, uuid: {uuid}")

        if jsonMsg.get("actuator_request_type").get("node_controller").get("node_request") is not None:
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug(f"_processMsg, node_request: {node_request}")

            # Parse out the component field in the node_request
            component = node_request[0:4]

            # Handle generic command line requests
            if component == 'SSPL':
                # Query the Zope GlobalSiteManager for an object implementing the MOTR actuator
                if self._command_line_actuator is None:
                    from actuators.Icommand_line import ICommandLine

                    command_line_actuator_class = self._queryUtility(ICommandLine)
                    # Instantiate CommandLine Actuator only if class is loaded
                    if command_line_actuator_class:
                        self._command_line_actuator = command_line_actuator_class(self._conf_reader)
                    else:
                        logger.warn("CommandLine Actuator not loaded")
                        json_msg = AckResponseMsg(node_request, NodeControllerMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return

                # Perform the request and get the response
                command_line_response = self._command_line_actuator.perform_request(jsonMsg).strip()
                self._log_debug(f"_process_msg, command line response: {command_line_response}")

                json_msg = AckResponseMsg(node_request, command_line_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # Handle LED effects using the HPI actuator
            elif component == "LED:":
                # HPI related operations are not supported in VM environment.
                if self._is_env_vm():
                    logger.warn("HPI operations are not supported in current environment")
                    return
                # Query the Zope GlobalSiteManager for an object implementing the IHPI actuator
                if self._HPI_actuator is None:
                    from actuators.Ihpi import IHPI
                    # Load HPIActuator class
                    HPI_actuator_class = self._queryUtility(IHPI)
                    # Instantiate HPIActuator only if class is loaded
                    if HPI_actuator_class:
                        self._HPI_actuator = HPI_actuator_class(self._conf_reader)
                    else:
                        logger.warn("HPIActuator not loaded")
                        if self._product.lower() in [x.lower() for x in enabled_products]:
                            json_msg = AckResponseMsg(node_request, NodeControllerMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                            self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return

                    self._log_debug(f"_process_msg, _HPI_actuator name: {self._HPI_actuator.name()}")

                    # Perform the request using HPI and get the response
                    hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                    self._log_debug(f"_process_msg, hpi_response: {hpi_response}")

                    json_msg = AckResponseMsg(node_request, hpi_response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # Set the Bezel LED color using the GEM interface
            elif component == "BEZE":
                # Query the Zope GlobalSiteManager for an object implementing the IGEM actuator
                if self._GEM_actuator is None:
                    self._GEM_actuator = self._queryUtility(IGEM)(self._conf_reader)
                    self._log_debug(f"_process_msg, _GEM_actuator name: {self._GEM_actuator.name()}")

                # Perform the request using GEM and get the response
                gem_response = self._GEM_actuator.perform_request(jsonMsg).strip()
                self._log_debug(f"_process_msg, gem_response: {gem_response}")

                json_msg = AckResponseMsg(node_request, gem_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "PDU:":
                # Query the Zope GlobalSiteManager for an object implementing the IPDU actuator
                if self._PDU_actuator is None:
                    from actuators.Ipdu import IPDU

                    PDU_actuator_class = self._queryUtility(IPDU)
                    # Instantiate RaritanPDU Actuator only if class is loaded
                    if PDU_actuator_class:
                        self._PDU_actuator = PDU_actuator_class(self._conf_reader)
                    else:
                        logger.warn("RaritanPDU Actuator not loaded")
                        json_msg = AckResponseMsg(node_request, NodeControllerMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return

                # Perform the request on the PDU and get the response
                pdu_response = self._PDU_actuator.perform_request(jsonMsg).strip()
                self._log_debug(f"_process_msg, pdu_response: {pdu_response}")

                json_msg = AckResponseMsg(node_request, pdu_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "RAID":
                # If the state is INITIALIZED, We can assume that actuator is
                # ready to perform operation.
                if actuator_state_manager.is_initialized("RAIDactuator"):
                    self._log_debug(f"_process_msg, _RAID_actuator name: {self._RAID_actuator.name()}")
                    self._execute_raid_request(
                        node_request, self._RAID_actuator, jsonMsg, uuid)

                # If the state is INITIALIZING, need to send message
                elif actuator_state_manager.is_initializing("RAIDactuator"):
                    # This state will not be reached. Kept here for consistency.
                    logger.info("RAID actuator is initializing")
                    busy_json_msg = AckResponseMsg(
                        node_request, "BUSY", uuid, error_no=errno.EBUSY).getJson()
                    self._write_internal_msgQ(
                        "RabbitMQegressProcessor", busy_json_msg)

                elif actuator_state_manager.is_imported("RAIDactuator"):
                    # This case will be for first request only. Subsequent
                    # requests will go to INITIALIZED state case.
                    logger.info("RAID actuator is imported and initializing")

                    from actuators.Iraid import IRAIDactuator
                    actuator_state_manager.set_state(
                            "RAIDactuator", actuator_state_manager.INITIALIZING)
                    # Query the Zope GlobalSiteManager for an object implementing the IRAIDactuator
                    raid_actuator_class = self._queryUtility(IRAIDactuator)
                    if raid_actuator_class:
                        # NOTE: Instantiation part should not time consuming
                        # otherwise NodeControllerMsgHandler will get block
                        # and will not be able serve any subsequent requests.
                        # This applies to instantiation of evey actuator.
                        self._RAID_actuator = raid_actuator_class()
                        logger.info(f"_process_msg, _RAID_actuator name: {self._RAID_actuator.name()}")
                        self._execute_raid_request(
                            node_request, self._RAID_actuator, jsonMsg, uuid)
                        actuator_state_manager.set_state(
                            "RAIDactuator", actuator_state_manager.INITIALIZED)
                    else:
                        logger.warn("RAID actuator is not instantiated")

                # If there is no entry for actuator in table, We can assume
                # that it is not loaded for some reason.
                else:
                    logger.warn("RAID actuator is not loaded or not supported")

            elif component == "IPMI":
                # Query the Zope GlobalSiteManager for an object implementing the IPMI actuator
                if self._IPMI_actuator is None:
                    from actuators.Iipmi import Iipmi

                    IPMI_actuator_class = self._queryUtility(Iipmi)
                    # Instantiate IPMI Actuator only if class is loaded
                    if IPMI_actuator_class:
                        self._IPMI_actuator = IPMI_actuator_class(self._conf_reader)
                    else:
                        logger.warn("IPMI Actuator not loaded")
                        json_msg = AckResponseMsg(node_request, NodeControllerMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return

                # Perform the IPMI request on the node and get the response
                ipmi_response = self._IPMI_actuator.perform_request(jsonMsg).strip()
                self._log_debug(f"_process_msg, ipmi_response: {ipmi_response}")

                json_msg = AckResponseMsg(node_request, ipmi_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "STOP":
                # HPI related operations are not supported in VM environment.
                if self._is_env_vm():
                    logger.warn("HPI operations are not supported in current environment")
                    return
                # Query the Zope GlobalSiteManager for an object implementing the IHPI actuator
                if self._HPI_actuator is None:
                    from actuators.Ihpi import IHPI
                    # Load HPIActuator class
                    HPI_actuator_class = self._queryUtility(IHPI)
                    # Instantiate HPIActuator only if class is loaded
                    if HPI_actuator_class:
                        self._HPI_actuator = HPI_actuator_class(self._conf_reader)
                    else:
                        logger.warn("HPIActuator not loaded")
                        if self._product.lower() in [x.lower() for x in enabled_products]:
                            json_msg = AckResponseMsg(node_request, NodeControllerMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                            self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return

                    self._log_debug(f"_process_msg, _HPI_actuator name: {self._HPI_actuator.name()}")

                    # Parse out the drive to stop
                    drive_request = node_request[12:].strip()
                    self._log_debug(f"perform_request, drive to stop: {drive_request}")

                    # Append POWER_OFF to notify HPI actuator of desired state
                    jsonMsg["actuator_request_type"]["node_controller"]["node_request"] = \
                            f"DISK: set {drive_request} POWER_OFF"
                    self._log_debug(f"_process_msg, jsonMsg: {jsonMsg}")

                    # Perform the request using HPI and get the response
                    hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                    self._log_debug(f"_process_msg, hpi_response: {hpi_response}")

                    # Simplify success message as external apps don't care about details
                    if "Success" in hpi_response:
                        hpi_response = "Successful"

                    json_msg = AckResponseMsg(node_request, hpi_response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "STAR":
                # HPI related operations are not supported in VM environment.
                if self._is_env_vm():
                    logger.warn("HPI operations are not supported in current environment")
                    return
                # Query the Zope GlobalSiteManager for an object implementing the IHPI actuator
                if self._HPI_actuator is None:
                    from actuators.Ihpi import IHPI
                    # Load HPIActuator class
                    HPI_actuator_class = self._queryUtility(IHPI)
                    # Instantiate HPIActuator only if class is loaded
                    if HPI_actuator_class:
                        self._HPI_actuator = HPI_actuator_class(self._conf_reader)
                    else:
                        logger.warn("HPIActuator not loaded")
                        if self._product.lower() in [x.lower() for x in enabled_products]:
                            json_msg = AckResponseMsg(node_request, NodeControllerMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                            self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return

                    self._log_debug(f"_process_msg, _HPI_actuator name: {self._HPI_actuator.name()}")

                    # Parse out the drive to start
                    drive_request = node_request[13:].strip()
                    self._log_debug(f"perform_request, drive to start: {drive_request}")

                    # Append POWER_ON to notify HPI actuator of desired state
                    jsonMsg["actuator_request_type"]["node_controller"]["node_request"] = \
                            f"DISK: set {drive_request} POWER_ON"
                    self._log_debug(f"_process_msg, jsonMsg: {jsonMsg}")

                    # Perform the request using HPI and get the response
                    hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                    self._log_debug(f"_process_msg, hpi_response: {hpi_response}")

                    # Simplify success message as external apps don't care about details
                    if "Success" in hpi_response:
                        hpi_response = "Successful"

                    json_msg = AckResponseMsg(node_request, hpi_response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)


            elif component == "RESE":
                # HPI related operations are not supported in VM environment.
                if self._is_env_vm():
                    logger.warn("HPI operations are not supported in current environment")
                    return
                # Query the Zope GlobalSiteManager for an object implementing the IHPI actuator
                if self._HPI_actuator is None:
                    from actuators.Ihpi import IHPI
                    # Load HPIActuator class
                    HPI_actuator_class = self._queryUtility(IHPI)
                    # Instantiate HPIActuator only if class is loaded
                    if HPI_actuator_class:
                        self._HPI_actuator = HPI_actuator_class(self._conf_reader)
                    else:
                        logger.warn("HPIActuator not loaded")
                        if self._product.lower() in [x.lower() for x in enabled_products]:
                            json_msg = AckResponseMsg(node_request, NodeControllerMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                            self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return

                    self._log_debug(f"_process_msg, _HPI_actuator name: {self._HPI_actuator.name()}")

                    # Parse out the drive to power cycle
                    drive_request = node_request[13:].strip()
                    self._log_debug(f"perform_request, drive to power cycle: {drive_request}")

                    # Append POWER_OFF and then POWER_ON to notify HPI actuator of desired state
                    jsonMsg["actuator_request_type"]["node_controller"]["node_request"] = \
                            f"DISK: set {drive_request} POWER_OFF"
                    self._log_debug(f"_process_msg, jsonMsg: {jsonMsg}")

                    # Perform the request using HPI and get the response
                    hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                    self._log_debug(f"_process_msg, hpi_response: {hpi_response}")

                    # Check for success and power the disk back on
                    if "Success" in hpi_response:
                        # Append POWER_ON to notify HPI actuator of desired state
                        jsonMsg["actuator_request_type"]["node_controller"]["node_request"] = \
                                   f"DISK: set {drive_request} POWER_ON"
                        self._log_debug(f"_process_msg, jsonMsg: {jsonMsg}")

                        # Perform the request using HPI and get the response
                        hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                        self._log_debug(f"_process_msg, hpi_response: {hpi_response}")

                            # Simplify success message as external apps don't care about details
                        if "Success" in hpi_response:
                            hpi_response = "Successful"

                    json_msg = AckResponseMsg(node_request, hpi_response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "HDPA":
                # If the state is INITIALIZED, We can assume that actuator is
                # ready to perform operation.
                if actuator_state_manager.is_initialized("Hdparm"):
                    logger.info(f"_process_msg, Hdparm_actuator name: {self._hdparm_actuator.name()}")
                    # Perform the hdparm request on the node and get the response
                    hdparm_response = self._hdparm_actuator.perform_request(jsonMsg).strip()
                    self._log_debug(f"_process_msg, hdparm_response: {hdparm_response}")

                    json_msg = AckResponseMsg(node_request, hdparm_response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                # If the state is INITIALIZING, need to send message
                elif actuator_state_manager.is_initializing("Hdparm"):
                    # This state will not be reached. Kept here for consistency.
                    logger.info("Hdparm actuator is initializing")
                    busy_json_msg = AckResponseMsg(
                        node_request, "BUSY", uuid, error_no=errno.EBUSY).getJson()
                    self._write_internal_msgQ(
                        "RabbitMQegressProcessor", busy_json_msg)

                elif actuator_state_manager.is_imported("Hdparm"):
                    # This case will be for first request only. Subsequent
                    # requests will go to INITIALIZED state case.
                    logger.info("Hdparm actuator is imported and initializing")
                    # Query the Zope GlobalSiteManager for an object
                    # implementing the hdparm actuator.
                    from actuators.Ihdparm import IHdparm
                    actuator_state_manager.set_state(
                            "Hdparm", actuator_state_manager.INITIALIZING)
                    hdparm_actuator_class = self._queryUtility(IHdparm)
                    if hdparm_actuator_class:
                        # NOTE: Instantiation part should not time consuming
                        # otherwise NodeControllerMsgHandler will get block and will
                        # not be able serve any subsequent requests. This applies
                        # to instantiation of evey actuator.
                        self._hdparm_actuator = hdparm_actuator_class()
                        self._log_debug(f"_process_msg, _hdparm_actuator name: {self._hdparm_actuator.name()}")
                        # Perform the hdparm request on the node and get the response
                        hdparm_response = self._hdparm_actuator.perform_request(jsonMsg).strip()
                        self._log_debug(f"_process_msg, hdparm_response: {hdparm_response}")

                        json_msg = AckResponseMsg(node_request, hdparm_response, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        actuator_state_manager.set_state(
                            "Hdparm", actuator_state_manager.INITIALIZED)
                    else:
                        logger.info("Hdparm actuator is not instantiated")

                # If there is no entry for actuator in table, We can assume
                # that it is not loaded for some reason.
                else:
                    logger.info("Hdparm actuator is not loaded or not supported")

            elif component == "SMAR":
                # Parse out the drive request field in json msg
                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                drive_request = node_request[12:].strip()
                self._log_debug(f"perform_request, drive: {drive_request}")

                # If the drive field is an asterisk then send all the smart results for all drives available
                if drive_request == "*":
                    # Send the event to DiskMonitor to schedule SMART test
                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "disk_smart_test",
                         "serial_number" : "*",
                         "node_request" : self.host_id,
                         "uuid" : uuid
                         })

                    self._write_internal_msgQ("DiskMonitor", internal_json_msg)
                    return

                # Put together a message to get the serial number of the drive using hdparm tool
                if drive_request.startswith("/"):
                    serial_number, error = self._retrieve_serial_number(drive_request)

                    # Send error response back on ack channel
                    if error != "":
                        json_msg = AckResponseMsg(node_request, error, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return
                else:
                    if self._smartctl_actuator is None:
                        from actuators.Ismartctl import ISmartctl
                        smartctl_actuator_class = self._queryUtility(ISmartctl)
                        if smartctl_actuator_class:
                            self._smartctl_actuator = self._queryUtility(ISmartctl)()
                            self._log_debug("_process_msg, _smart_actuator name: %s" % self._smartctl_actuator.name())
                        else:
                            logger.error(" No module Smartctl is present to load")
                    serial_compare = self._smartctl_actuator._check_serial_number(drive_request)
                    if not serial_compare:
                        json_msg = AckResponseMsg(node_request, "Drive Not Found", uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return
                    else:
                        serial_number = drive_request

                    # Send the event to DiskMonitor to schedule SMART test
                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "disk_smart_test",
                            "serial_number" : serial_number,
                            "node_request" : node_request,
                            "uuid" : uuid
                        })

                    self._write_internal_msgQ("DiskMonitor", internal_json_msg)

            elif component == "DRVM":
                # Requesting the current status from drivemanager
                # Parse out the drive request field in json msg
                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                drive_request = node_request[15:].strip()
                self._log_debug(f"perform_request, drive: {drive_request}")

                # If the drive field is an asterisk then send all the drivemanager results for all drives available
                if drive_request == "*":
                    # Send a message to the disk message handler to lookup the drivemanager status and send it out
                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "drvmngr_status",
                         "serial_number" : "*",
                         "node_request" : self.host_id,
                         "uuid" : uuid
                         })

                    # Send the event to disk message handler to generate json message
                    self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)
                    return

                # Put together a message to get the serial number of the drive using hdparm tool
                if drive_request.startswith("/"):
                    serial_number, error = self._retrieve_serial_number(drive_request)

                    # Send error response back on ack channel
                    if error != "":
                        json_msg = AckResponseMsg(node_request, error, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return
                else:
                    serial_number = drive_request

                # Send a message to the disk message handler to lookup the smart status and send it out
                internal_json_msg = json.dumps(
                    {"sensor_request_type" : "drvmngr_status",
                     "serial_number" : serial_number,
                     "node_request" : node_request,
                     "uuid" : uuid
                    })

                # Send the event to disk message handler to generate json message
                self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

            elif component == "HPI_":
                # Requesting the current status from HPI data
                # Parse out the drive request field in json msg
                if self._is_env_vm():
                    logger.warn("HPI operations are not supported in current environment")
                    return

                if self.setup == 'cortx':
                    logger.warn("HPIMonitor not loaded")
                    json_msg = AckResponseMsg(node_request, NodeControllerMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                    return

                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                drive_request = node_request[11:].strip()
                self._log_debug(f"perform_request, drive: {drive_request}")

                # If the drive field is an asterisk then send all the hpi results for all drives available
                if drive_request == "*":
                    # Send a message to the disk message handler to lookup the hpi status and send it out
                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "hpi_status",
                         "serial_number" : "*",
                         "node_request" : self.host_id,
                         "uuid" : uuid
                         })

                    # Send the event to disk message handler to generate json message
                    self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)
                    return

                # Put together a message to get the serial number of the drive using hdparm tool
                if drive_request.startswith("/"):
                    serial_number, error = self._retrieve_serial_number(drive_request)

                    # Send error response back on ack channel
                    if error != "":
                        json_msg = AckResponseMsg(node_request, error, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return
                else:
                    serial_number = drive_request

                # Send a message to the disk message handler to lookup the smart status and send it out
                internal_json_msg = json.dumps(
                    {"sensor_request_type" : "hpi_status",
                     "serial_number" : serial_number,
                     "node_request" : node_request,
                     "uuid" : uuid
                    })

                # Send the event to disk message handler to generate json message
                self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

            elif component == "SIMU":
                # Requesting to simulate an event
                # Parse out the simulated request field
                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                sim_request = node_request[9:].strip().split(" ")
                self._log_debug(f"perform_request, sim_request: {str(sim_request)}")

                # Put together a message to get the serial number of the drive using hdparm tool
                if sim_request[1].startswith("/"):
                    serial_number, error = self._retrieve_serial_number(sim_request[1])

                    # Send error response back on ack channel
                    if error != "":
                        json_msg = AckResponseMsg(node_request, error, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                        return
                else:
                    serial_number = sim_request[1]

                # SMART simulation requests are sent to DiskMonitor
                if sim_request[0] == "SMART_FAILURE":
                    logger.info(f"NodeControllerMsgHandler, simulating SMART_FAILURE on drive: {serial_number}")

                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "simulate_failure",
                         "serial_number" : serial_number,
                         "node_request" : sim_request[0],
                         "uuid" : uuid
                         })

                    # Send the event to DiskMonitor to handle it from here
                    self._write_internal_msgQ("DiskMonitor", internal_json_msg)

                else:
                    # Send a message to the disk message handler to handle simulation request
                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "sim_event",
                         "serial_number" : serial_number,
                         "node_request" : sim_request[0],
                         "uuid" : uuid
                         })

                    # Send the event to disk message handler to generate json message
                    self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

            elif component == "NDHW":
                # NDHW Stands for Node HW.
                try:
                    # Load and Instantiate the Actuator for the first request
                    if self._NodeHW_actuator is None:
                        from actuators.impl.generic.node_hw import NodeHWactuator
                        from framework.utils.ipmi_client import IpmiFactory
                        self.ipmi_client_name = Conf.get(SSPL_CONF, f"{self.NODE_HW_ACTUATOR}>{self.IPMI_IMPLEMENTOR}",
                            "ipmitool")
                        ipmi_factory = IpmiFactory()
                        ipmi_client = \
                           ipmi_factory.get_implementor(self.ipmi_client_name)
                        # Instantiate NodeHWactuator only if class is loaded
                        if ipmi_client is not None:
                            self._NodeHW_actuator = NodeHWactuator(ipmi_client, self._conf_reader)
                            self._NodeHW_actuator.initialize()
                        else:
                            logger.error(f"IPMI client: '{self.ipmi_client_name}' doesn't exist")
                            return
                    node_request = jsonMsg.get("actuator_request_type")
                    # Perform the NodeHW request on the node and get the response
                    #TODO: Send message to Ack as well as Sensor in their respective channel.
                    node_hw_response = self._NodeHW_actuator.perform_request(node_request)
                    self._log_debug(f"_process_msg, node_hw_response: {node_hw_response}")
                    json_msg = NodeHwAckResponseMsg(node_request, node_hw_response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                except ImportError as e:
                    logger.error(f"Modules could not be loaded: {e}")
                    return
                except Exception as e:
                    logger.error(f"NodeControllerMsgHandler, _process_msg, Exception in request handling: {e}")
                    return

            else:
                response = f"NodeControllerMsgHandler, _process_msg, unknown node controller msg: {node_request}"
                self._log_debug(response)

                json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # ... handle other node message types

    def _retrieve_serial_number(self, drive_request):
        """Retrieves serial number using smartctl tool with /dev/* path"""
        serial_number = "Not Found"
        error = ""

        try:
            # Query the Zope GlobalSiteManager for an object implementing the smart actuator
            if self._smartctl_actuator is None:
                from actuators.Ismartctl import ISmartctl
                smartctl_actuator_class = self._queryUtility(ISmartctl)
                if smartctl_actuator_class:
                    self._smartctl_actuator = self._queryUtility(ISmartctl)()
                    self._log_debug("_process_msg, _smart_actuator name: %s" % self._smartctl_actuator.name())
                else:
                    logger.exception("_retrieve_serial_number, No module Smartctl is present to load")
                    return serial_number, error

            # Forming a request to get serial number of a drive using smartctl tool
            smartctl_request = "SMARTCTL: GET_SERIAL {}".format(drive_request)
            serial_num_msg = {
                 "actuator_request_type": {
                    "node_controller": {
                        "node_request": smartctl_request
                        }
                    }
                 }

            # Send a request to the smartctl actuator to get the serial number of the device
            smartctl_response = self._smartctl_actuator.perform_request(serial_num_msg).strip()
            self._log_debug("_process_msg, smartctl_response: %s" % smartctl_response)

            # Return the error if the response contains one
            if "error" in smartctl_response.lower():
                error = smartctl_response
            else:
                # Parse out "Serial Number:" from smartctl result to obtain serial number
                serial_number = smartctl_response[14:].strip()

        except Exception as ae:
            logger.exception(ae)
            error = str(ae)

        return serial_number, error

    def _execute_raid_request(self, node_request, actuator_instance, json_msg, uuid):
        """Performs a RAID request by calling perform_request method of a RAID
           actuator.
        """
        # Perform the RAID request on the node and get the response
        raid_response = actuator_instance.perform_request(json_msg).strip()
        self._log_debug(f"_process_msg, raid_response: {raid_response}")

        json_msg = AckResponseMsg(node_request, raid_response, uuid).getJson()
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

        # Restart openhpid to update HPI data only if it is a H/W environment
        if self.setup in [ "hw", "ssu" ]:
            self._log_debug("restarting openhpid service to update HPI data")
            if "assemble" in json_msg.get("actuator_request_type").get("node_controller").get("node_request").lower():
                internal_json_msg = json.dumps(
                                    {"actuator_request_type": {
                                    "service_controller": {
                                        "service_name" : "openhpid.service",
                                        "service_request": "restart"
                                    }}})
                self._write_internal_msgQ(ServiceMsgHandler.name(), internal_json_msg)

    def _is_env_vm(self):
        """Retrieves the current setup and returns True|False based on setup value."""
        setup = Conf.get(GLOBAL_CONF, f"{RELEASE}>{self.SETUP}",
                                                          "ssu")
        return setup.lower() in ['gw', 'cmu', 'vm']

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(NodeControllerMsgHandler, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(NodeControllerMsgHandler, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(NodeControllerMsgHandler, self).shutdown()
