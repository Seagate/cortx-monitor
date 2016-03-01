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
from actuators.Ireset_drive import IResetDrive
from actuators.Ihdparm import IHdparm

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

        self.ip_addr = socket.gethostbyname(socket.getfqdn())

        self._PDU_actuator         = None
        self._RAID_actuator        = None
        self._IPMI_actuator        = None
        self._hdparm_actuator      = None
        self._reset_drive_actuator = None

        self._set_debug(True)
        self._set_debug_persist(True)

    def run(self):
        """Run the module periodically on its own thread."""
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
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request") + \
                            " " + self.ip_addr
            self._log_debug("_processMsg, node_request: %s" % node_request)

            # Parse out the component field in the node_request
            component = node_request[0:4]

            if component == "PDU:":
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

            elif component == "RESE":
                # Query the Zope GlobalSiteManager for an object implementing the reset drive actuator
                if self._reset_drive_actuator is None:
                    self._reset_drive_actuator = queryUtility(IResetDrive)()
                    self._log_debug("_process_msg, _reset_drive_actuator name: %s" % self._reset_drive_actuator.name())

                # Perform the drive reset request on the node and get the response
                reset_response = self._reset_drive_actuator.perform_request(jsonMsg)
                self._log_debug("_process_msg, reset_response: %s" % reset_response)

                json_msg = AckResponseMsg(node_request, reset_response, uuid).getJson()
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
                self._log_debug("perform_request, drive request: %s" % drive_request)

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

                    # Stop here if we have an error
                    if "Error" in hdparm_response:
                        json_msg = AckResponseMsg(node_request + " " + self.ip_addr, hdparm_response, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                    else:
                        # Parse out "Serial Number:" from hdparm result to obtain serial number
                        serial_number = hdparm_response[15:].strip()
                else:
                    serial_number = drive_request

                # Send a message to the disk message handler to lookup the smart status and send it out
                internal_json_msg = json.dumps(
                    {"sensor_request_type" : "disk_smart_test",
                        "serial_number" : serial_number,
                        "node_request" : node_request  + " " + self.ip_addr,
                        "uuid" : uuid
                    })

                # Send the event to disk message handler to generate json message
                self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

            elif component == "DRVM":
                # Requesting the current status from drivemanager
                # Parse out the drive request field in json msg
                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                drive_request = node_request[15:].strip()
                self._log_debug("perform_request, drive request: %s" % drive_request)

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

                    # Stop here if we have an error
                    if "Error" in hdparm_response:
                        json_msg = AckResponseMsg(node_request + " " + self.ip_addr, hdparm_response, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                    else:
                        # Parse out "Serial Number:" from hdparm result to obtain serial number
                        serial_number = hdparm_response[15:].strip()
                else:
                    serial_number = drive_request

                # Send a message to the disk message handler to lookup the smart status and send it out
                internal_json_msg = json.dumps(
                    {"sensor_request_type" : "drvmngr_status",
                     "serial_number" : serial_number,
                     "node_request" : node_request  + " " + self.ip_addr,
                     "uuid" : uuid
                    })

                # Send the event to disk message handler to generate json message
                self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

            elif component == "HPI_":
                # Requesting the current status from HPI data
                # Parse out the drive request field in json msg
                node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
                drive_request = node_request[11:].strip()
                self._log_debug("perform_request, drive request: %s" % drive_request)

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

                if drive_request.startswith("/"):
                    # Query the Zope GlobalSiteManager for an object implementing the hdparm actuator
                    if self._hdparm_actuator is None:
                        self._hdparm_actuator = queryUtility(IHdparm)()
                        self._log_debug("_process_msg, _hdparm_actuator name: %s" % self._hdparm_actuator.name())

                    # Put together a message to get the serial number of the drive using hdparm tool
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

                    # Stop here if we have an error
                    if "Error" in hdparm_response:
                        json_msg = AckResponseMsg(node_request + " " + self.ip_addr, hdparm_response, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                    else:
                        # Parse out "Serial Number:" from hdparm result to obtain serial number
                        serial_number = hdparm_response[15:].strip()
                else:
                    serial_number = drive_request

                # Send a message to the disk message handler to lookup the smart status and send it out
                internal_json_msg = json.dumps(
                    {"sensor_request_type" : "hpi_status",
                     "serial_number" : serial_number,
                     "node_request" : node_request  + " " + self.ip_addr,
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


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(NodeControllerMsgHandler, self).shutdown()