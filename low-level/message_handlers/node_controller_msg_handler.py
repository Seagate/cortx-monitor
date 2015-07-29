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

import json
import time

from actuators.ILogin import ILogin
from actuators.Ipdu import IPDU
from actuators.Iraid import IRAIDactuator

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from json_msgs.messages.actuators.ack_response import AckResponseMsg

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

        self._PDU_actuator  = None
        self._RAID_actuator = None

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

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.exception("NodeControllerMsgHandler restarting")

        self._scheduler.enter(0, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger"""
        self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

        if isinstance(jsonMsg, dict) == False:
            jsonMsg = json.loads(jsonMsg)

        if jsonMsg.get("actuator_request_type").get("node_controller").get("node_request") is not None:
            node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
            self._log_debug("_processMsg, node_request: %s" % node_request)

            # Parse out the component field in the node_request
            component = node_request[0:4]

            if component == "PDU:":
                # Query the Zope GlobalSiteManager for an object implementing the IPDU actuator
                if self._PDU_actuator is None:
                    self._PDU_actuator = queryUtility(IPDU)(self._conf_reader)
                    self._log_debug("_process_msg, _PDU_actuator name: %s" % self._PDU_actuator.name())

                # Perform the request on the PDU and get the response
                pdu_response = self._PDU_actuator.perform_request(jsonMsg)
                self._log_debug("_process_msg, pdu_response: %s" % pdu_response)

                json_msg = AckResponseMsg(node_request, pdu_response).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            if component == "RAID":
                # Query the Zope GlobalSiteManager for an object implementing the IPDU actuator
                if self._RAID_actuator is None:
                    self._RAID_actuator = queryUtility(IRAIDactuator)()
                    self._log_debug("_process_msg, _RAID_actuator name: %s" % self._RAID_actuator.name())

                # Perform the RAID request on the node and get the response
                raid_response = self._RAID_actuator.perform_request(jsonMsg)
                self._log_debug("_process_msg, raid_response: %s" % raid_response)

                json_msg = AckResponseMsg(node_request, raid_response).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # ... handle other node message types


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(NodeControllerMsgHandler, self).shutdown()