"""
 ****************************************************************************
 Filename:          node_controller_msg_handler.py
 Description:       Message Handler for controlling the node
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

import socket
import json
import time

from actuators.ILogin import ILogin
from actuators.Ipdu import IPDU
from actuators.Iraid import IRAIDactuator
from actuators.Iipmi import Iipmi
from actuators.Ihdparm import IHdparm
from actuators.Ihpi import IHPI
from actuators.Ispiel import ISpiel
from actuators.Icommand_line import ICommandLine

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from json_msgs.messages.actuators.ack_response import AckResponseMsg

from message_handlers.disk_msg_handler import DiskMsgHandler
from zope.component import queryUtility


class NodeControllerMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for controlling the node"""

    MODULE_NAME = "NodeControllerMsgHandler"
    PRIORITY    = 2

    @staticmethod
    def name():
        """ @return: name of the module."""
        return NodeControllerMsgHandler.MODULE_NAME

    def __init__(self):
        super(NodeControllerMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(NodeControllerMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(NodeControllerMsgHandler, self).initialize_msgQ(msgQlist)

        # Find a meaningful hostname to be used
        if socket.gethostname().find('.') >= 0:
            self.ip_addr = socket.gethostname()
        else:
            self.ip_addr = socket.gethostbyaddr(socket.gethostname())[0]

        self._spiel_actuator        = None
        self._HPI_actuator          = None
        self._GEM_actuator          = None
        self._PDU_actuator          = None
        self._RAID_actuator         = None
        self._IPMI_actuator         = None
        self._hdparm_actuator       = None
        self._command_line_actuator = None

    def run(self):
        """Run the module periodically on its own thread."""
        self._set_debug(True)
        self._set_debug_persist(True)
        self._log_debug("Start accepting requests")

        try:
            # Block on message queue until it contains an entry
            jsonMsg = self._read_my_msgQ()
            if jsonMsg is not None:
                self._process_msg(jsonMsg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                jsonMsg = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._process_msg(jsonMsg)

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception("NodeControllerMsgHandler restarting: %s" % ae)

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and handles appropriately"""
        self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

        if isinstance(jsonMsg, dict) == False:
            jsonMsg = json.loads(jsonMsg)

        # Parse out the uuid so that it can be sent back in Ack message
        uuid = None
        if jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            self._log_debug("_processMsg, uuid: %s" % uuid)

        if jsonMsg.get("actuator_request_type").get("node_controller").get("node_request") is not None:
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("_processMsg, node_request: %s" % node_request)

            # Parse out the component field in the node_request
            component = node_request[0:4]


            # Handle generic command line requests
            if component == 'SSPL':
                # Query the Zope GlobalSiteManager for an object implementing the IMERO actuator
                if self._command_line_actuator is None:
                    self._command_line_actuator = queryUtility(ICommandLine)(self._conf_reader)
                    self._log_debug("_process_msg, _command_line_actuator name: %s" % self._command_line_actuator.name())

                # Perform the request and get the response
                command_line_response = self._command_line_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, command line response: %s" % command_line_response)

                json_msg = AckResponseMsg(node_request, command_line_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # Handle requests related to Mero
            elif component == 'MERO':
                # Query the Zope GlobalSiteManager for an object implementing the IMERO actuator
                if self._spiel_actuator is None:
                    self._spiel_actuator = queryUtility(ISpiel)(self._conf_reader)
                    self._log_debug("_process_msg, _spiel_actuator name: %s" % self._spiel_actuator.name())

                # Perform the request and get the response
                spiel_response = self._spiel_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, spiel response: %s" % spiel_response)

                json_msg = AckResponseMsg(node_request, spiel_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # Handle LED effects using the HPI actuator
            elif component == "LED:":
                # Query the Zope GlobalSiteManager for an object implementing the IHPI actuator
                if self._HPI_actuator is None:
                    self._HPI_actuator = queryUtility(IHPI)(self._conf_reader)
                    self._log_debug("_process_msg, _HPI_actuator name: %s" % self._HPI_actuator.name())

                # Perform the request using HPI and get the response
                hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, hpi_response: %s" % hpi_response)

                json_msg = AckResponseMsg(node_request, hpi_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # Set the Bezel LED color using the GEM interface
            elif component == "BEZE":
                # Query the Zope GlobalSiteManager for an object implementing the IGEM actuator
                if self._GEM_actuator is None:
                    self._GEM_actuator = queryUtility(IGEM)(self._conf_reader)
                    self._log_debug("_process_msg, _GEM_actuator name: %s" % self._GEM_actuator.name())

                # Perform the request using GEM and get the response
                gem_response = self._GEM_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, gem_response: %s" % gem_response)

                json_msg = AckResponseMsg(node_request, gem_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "PDU:":
                # Query the Zope GlobalSiteManager for an object implementing the IPDU actuator
                if self._PDU_actuator is None:
                    self._PDU_actuator = queryUtility(IPDU)(self._conf_reader)
                    self._log_debug("_process_msg, _PDU_actuator name: %s" % self._PDU_actuator.name())

                # Perform the request on the PDU and get the response
                pdu_response = self._PDU_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, pdu_response: %s" % pdu_response)

                json_msg = AckResponseMsg(node_request, pdu_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "RAID":
                # Query the Zope GlobalSiteManager for an object implementing the IRAIDactuator
                if self._RAID_actuator is None:
                    self._RAID_actuator = queryUtility(IRAIDactuator)()
                    self._log_debug("_process_msg, _RAID_actuator name: %s" % self._RAID_actuator.name())

                # Perform the RAID request on the node and get the response
                raid_response = self._RAID_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, raid_response: %s" % raid_response)

                json_msg = AckResponseMsg(node_request, raid_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "IPMI":
                # Query the Zope GlobalSiteManager for an object implementing the IPMI actuator
                if self._IPMI_actuator is None:
                    self._IPMI_actuator = queryUtility(Iipmi)(self._conf_reader)
                    self._log_debug("_process_msg, _IPMI_actuator name: %s" % self._IPMI_actuator.name())

                # Perform the RAID request on the node and get the response
                ipmi_response = self._IPMI_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, ipmi_response: %s" % ipmi_response)

                json_msg = AckResponseMsg(node_request, ipmi_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "STOP":
                # Query the Zope GlobalSiteManager for an object implementing the IHPI actuator
                if self._HPI_actuator is None:
                    self._HPI_actuator = queryUtility(IHPI)(self._conf_reader)
                    self._log_debug("_process_msg, _HPI_actuator name: %s" % self._HPI_actuator.name())

                # Parse out the drive to stop
                drive_request = node_request[12:].strip()
                self._log_debug("perform_request, drive to stop: %s" % drive_request)

                # Append POWER_OFF to notify HPI actuator of desired state
                jsonMsg["actuator_request_type"]["node_controller"]["node_request"] = \
                        "DISK: set {} POWER_OFF".format(drive_request)
                self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

                # Perform the request using HPI and get the response
                hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, hpi_response: %s" % hpi_response)

                # Simplify success message as external apps don't care about details
                if "Success" in hpi_response:
                    hpi_response = "Successful"

                json_msg = AckResponseMsg(node_request, hpi_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "STAR":
                # Query the Zope GlobalSiteManager for an object implementing the IHPI actuator
                if self._HPI_actuator is None:
                    self._HPI_actuator = queryUtility(IHPI)(self._conf_reader)
                    self._log_debug("_process_msg, _HPI_actuator name: %s" % self._HPI_actuator.name())

                # Parse out the drive to start
                drive_request = node_request[13:].strip()
                self._log_debug("perform_request, drive to start: %s" % drive_request)

                # Append POWER_ON to notify HPI actuator of desired state
                jsonMsg["actuator_request_type"]["node_controller"]["node_request"] = \
                        "DISK: set {} POWER_ON".format(drive_request)
                self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

                # Perform the request using HPI and get the response
                hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, hpi_response: %s" % hpi_response)

                # Simplify success message as external apps don't care about details
                if "Success" in hpi_response:
                    hpi_response = "Successful"

                json_msg = AckResponseMsg(node_request, hpi_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                # Perform the request using HPI and get the response
                hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, hpi_response: %s" % hpi_response)

            elif component == "RESE":
                # Query the Zope GlobalSiteManager for an object implementing the IHPI actuator
                if self._HPI_actuator is None:
                    self._HPI_actuator = queryUtility(IHPI)(self._conf_reader)
                    self._log_debug("_process_msg, _HPI_actuator name: %s" % self._HPI_actuator.name())

                # Parse out the drive to power cycle
                drive_request = node_request[13:].strip()
                self._log_debug("perform_request, drive to power cycle: %s" % drive_request)

                # Append POWER_OFF and then POWER_ON to notify HPI actuator of desired state
                jsonMsg["actuator_request_type"]["node_controller"]["node_request"] = \
                        "DISK: set {} POWER_OFF".format(drive_request)
                self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

                # Perform the request using HPI and get the response
                hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, hpi_response: %s" % hpi_response)

                # Check for success and power the disk back on
                if "Success" in hpi_response:
                    # Pause to allow time for disk to power down
                    time.sleep(10)

                    # Append POWER_ON to notify HPI actuator of desired state
                    jsonMsg["actuator_request_type"]["node_controller"]["node_request"] = \
                               "DISK: set {} POWER_ON".format(drive_request)
                    self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

                    # Perform the request using HPI and get the response
                    hpi_response = self._HPI_actuator.perform_request(jsonMsg).strip()
                    self._log_debug("_process_msg, hpi_response: %s" % hpi_response)

                    # Simplify success message as external apps don't care about details
                    if "Success" in hpi_response:
                        # Pause to allow time for power on so external apps don't rush off
                        time.sleep(45)

                        hpi_response = "Successful"

                json_msg = AckResponseMsg(node_request, hpi_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "HDPA":
                # Query the Zope GlobalSiteManager for an object implementing the hdparm actuator
                if self._hdparm_actuator is None:
                    self._hdparm_actuator = queryUtility(IHdparm)()
                    self._log_debug("_process_msg, _hdparm_actuator name: %s" % self._hdparm_actuator.name())

                # Perform the hdparm request on the node and get the response
                hdparm_response = self._hdparm_actuator.perform_request(jsonMsg).strip()
                self._log_debug("_process_msg, hdparm_response: %s" % hdparm_response)

                json_msg = AckResponseMsg(node_request, hdparm_response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif component == "SMAR":
                # Parse out the drive request field in json msg
                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                drive_request = node_request[12:].strip()
                self._log_debug("perform_request, drive: %s" % drive_request)

                # If the drive field is an asterisk then send all the smart results for all drives available
                if drive_request == "*":
                    # Send a message to the disk message handler to lookup the smart status and send it out
                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "disk_smart_test",
                         "serial_number" : "*",
                         "node_request" : self.ip_addr,
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
                    {"sensor_request_type" : "disk_smart_test",
                        "serial_number" : serial_number,
                        "node_request" : node_request,
                        "uuid" : uuid
                    })

                # Send the event to disk message handler to generate json message
                self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

            elif component == "DRVM":
                # Requesting the current status from drivemanager
                # Parse out the drive request field in json msg
                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                drive_request = node_request[15:].strip()
                self._log_debug("perform_request, drive: %s" % drive_request)

                # If the drive field is an asterisk then send all the drivemanager results for all drives available
                if drive_request == "*":
                    # Send a message to the disk message handler to lookup the drivemanager status and send it out
                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "drvmngr_status",
                         "serial_number" : "*",
                         "node_request" : self.ip_addr,
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
                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                drive_request = node_request[11:].strip()
                self._log_debug("perform_request, drive: %s" % drive_request)

                # If the drive field is an asterisk then send all the hpi results for all drives available
                if drive_request == "*":
                    # Send a message to the disk message handler to lookup the hpi status and send it out
                    internal_json_msg = json.dumps(
                        {"sensor_request_type" : "hpi_status",
                         "serial_number" : "*",
                         "node_request" : self.ip_addr,
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
            else:
                response = "NodeControllerMsgHandler, _process_msg, unknown node controller msg: {}" \
                            .format(node_request)
                self._log_debug(response)

                json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # ... handle other node message types

    def _retrieve_serial_number(self, drive_request):
        """Use the /dev/* path in hdparm tool to retrieve serial number"""
        serial_number = "Not Found"
        error = ""

        try:
            # Query the Zope GlobalSiteManager for an object implementing the hdparm actuator
            if self._hdparm_actuator is None:
                self._hdparm_actuator = queryUtility(IHdparm)()
                self._log_debug("_process_msg, _hdparm_actuator name: %s" % self._hdparm_actuator.name())

            hd_parm_request = "HDPARM: -I {} | grep 'Serial Number:'".format(drive_request)
            serial_num_msg = {
                 "actuator_request_type": {
                    "node_controller": {
                        "node_request": hd_parm_request
                        }
                    }
                 }

            # Send a request to the hdparm tool to get the serial number of the device
            hdparm_response = self._hdparm_actuator.perform_request(serial_num_msg).strip()
            self._log_debug("_process_msg, hdparm_response: %s" % hdparm_response)

            # Return the error if the response contains one
            if "Error" in hdparm_response:
                error = hdparm_response
            else:
                # Parse out "Serial Number:" from hdparm result to obtain serial number
                serial_number = hdparm_response[15:].strip()

        except Exception as ae:
            logger.exception(ae)
            error = str(ae)

        return serial_number, error

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(NodeControllerMsgHandler, self).shutdown()