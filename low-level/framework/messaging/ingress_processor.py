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
  Description:       Handles outgoing messages via messaging bus system
 ****************************************************************************
"""

import ctypes
import json
import os
import time
import socket

from cortx.utils.message_bus import MessageConsumer
from jsonschema import Draft3Validator, validate

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.base.sspl_constants import RESOURCE_PATH
from framework.messaging.egress_processor import \
    EgressProcessor
from framework.utils.conf_utils import CLUSTER, SRVNODE, SSPL_CONF, Conf
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.ack_response import AckResponseMsg
from . import producer_initialized

try:
    use_security_lib = True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info(
        "libsspl_sec not found, disabling authentication on ingress msgs")
    use_security_lib = False


class IngressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles incoming messages via message bus."""

    MODULE_NAME = "IngressProcessor"
    PRIORITY = 1

    # Section and keys in configuration file
    PROCESSOR = MODULE_NAME.upper()
    CONSUMER_ID = "consumer_id"
    CONSUMER_GROUP = "consumer_group"
    MESSAGE_TYPE = "message_type"
    OFFSET = "offset"
    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
    CLUSTER_ID_KEY = 'cluster_id'
    NODE_ID_KEY = 'node_id'

    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Request.json"
    JSON_SENSOR_SCHEMA = "SSPL-LL_Sensor_Request.json"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return IngressProcessor.MODULE_NAME

    def __init__(self):
        super(IngressProcessor, self).__init__(self.MODULE_NAME,
                                                       self.PRIORITY)

        # Read in the actuator schema for validating messages
        schema_file = os.path.join(RESOURCE_PATH + '/actuators',
                                   self.JSON_ACTUATOR_SCHEMA)
        self._actuator_schema = self._load_schema(schema_file)

        # Read in the sensor schema for validating messages
        schema_file = os.path.join(RESOURCE_PATH + '/sensors',
                                   self.JSON_SENSOR_SCHEMA)
        self._sensor_schema = self._load_schema(schema_file)

    def _load_schema(self, schema_file):
        """Loads a schema from a file and validates

        @param string schema_file     location of schema on the file system
        @return string                Trimmed and validated schema
        """
        with open(schema_file, 'r') as f:
            schema = json.load(f)

        # Validate the schema to conform to Draft 3 specification
        Draft3Validator.check_schema(schema)

        return schema

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(IngressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(IngressProcessor, self).initialize_msgQ(msgQlist)

        self._read_config()
        producer_initialized.wait()
        self._consumer = MessageConsumer(consumer_id=self._consumer_id,
                                         consumer_group=self._consumer_group,
                                         message_types=[self._message_type],
                                         auto_ack=False, offset=self._offset)

    def run(self):
        # self._set_debug(True)
        # self._set_debug_persist(True)

        # time.sleep(180)
        logger.info(
            "IngressProcessor, Initialization complete, accepting requests")

        try:
            while True:
                message = self._consumer.receive()
                if message:
                    logger.info(
                        f"IngressProcessor, Message Recieved: {message}")
                    self._process_msg(message)
                    self._consumer.ack()
                else:
                    time.sleep(1)
        except Exception as e:
            if self.is_running() is True:
                logger.info(
                    "IngressProcessor ungracefully breaking out of run loop, restarting.")
                logger.error("IngressProcessor, Exception: %s" % str(e))
                self._scheduler.enter(10, self._priority, self.run, ())
            else:
                logger.info(
                    "IngressProcessor gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, body):
        """Parses the incoming message and hands off to the appropriate module"""

        ingressMsg = {}
        uuid = None
        hostname = socket.gethostname()
        try:
            if isinstance(body, dict) is False:
                ingressMsg = json.loads(body)
            else:
                ingressMsg = body

            # Authenticate message using username and signature fields
            username = ingressMsg.get("username")
            signature = ingressMsg.get("signature")
            message = ingressMsg.get("message")
            uuid = ingressMsg.get("uuid")
            msg_len = len(message) + 1

            if uuid is None:
                uuid = "N/A"

            if use_security_lib and \
                    SSPL_SEC.sspl_verify_message(msg_len, str(message),
                                                 username, signature) != 0:
                logger.warn(
                    "IngressProcessor, Authentication failed on message: %s" % ingressMsg)
                return

            # Get the incoming message type
            if message.get("actuator_request_type") is not None:
                msgType = message.get("actuator_request_type")

                # Validate against the actuator schema
                validate(ingressMsg, self._actuator_schema)

            elif message.get("sensor_request_type") is not None:
                msgType = message.get("sensor_request_type")

                # Validate against the sensor schema
                validate(ingressMsg, self._sensor_schema)

            else:
                # We only handle incoming actuator and sensor requests, ignore
                # everything else.
                return

            # Check for debugging being activated in the message header
            self._check_debug(message)
            self._log_debug("_process_msg, ingressMsg: %s" % ingressMsg)

            # Compare hostname from the request to determine
            # if request is meant for the current node
            node_identifier = ingressMsg.get("node_identifier")
            if node_identifier is None:
                logger.warning(
                    "Required attribute node_identifier is missing from actuator request")
                return
            elif node_identifier == hostname:
                self._send_to_msg_handler(msgType, message, uuid)
            else:
                logger.info(
                    "Node identifier mismatch, actuator request rejected.")
                return

        except Exception:
            logger.error(
                "IngressProcessor, _process_msg unrecognized message: %r" % ingressMsg)
            ack_msg = AckResponseMsg("Error Processing Msg",
                                     "Msg Handler Not Found", uuid).getJson()
            self._write_internal_msgQ(EgressProcessor.name(), ack_msg)

    def _send_to_msg_handler(self, msgType, message, uuid):
        # Hand off to appropriate actuator message handler
        if msgType.get("thread_controller") is not None:
            self._write_internal_msgQ("ThreadController", message)

        elif msgType.get("service_controller") is not None:
            self._write_internal_msgQ("ServiceMsgHandler", message)

        elif msgType.get("node_controller") is not None:
            self._write_internal_msgQ("NodeControllerMsgHandler", message)

        elif msgType.get("storage_enclosure") is not None:
            self._write_internal_msgQ("RealStorActuatorMsgHandler", message)

        # Hand off to appropriate sensor message handler
        elif msgType.get("node_data") is not None:
            self._write_internal_msgQ("NodeDataMsgHandler", message)

        elif msgType.get("enclosure_alert") is not None:
            self._write_internal_msgQ("RealStorEnclMsgHandler", message)

        elif msgType.get("storage_enclosure") is not None:
            self._write_internal_msgQ("RealStorActuatorMsgHandler", message)
        # ... handle other incoming messages that have been validated
        else:
            # Send ack about not finding a msg handler
            ack_msg = AckResponseMsg("Error Processing Message",
                                     "Message Handler Not Found",
                                     uuid).getJson()
            self._write_internal_msgQ(EgressProcessor.name(),
                                      ack_msg)

    def _read_config(self):
        """Read config for messaging bus."""
        # Make methods locally available
        self._node_id = Conf.get(SSPL_CONF,
                                 f"{CLUSTER}>{SRVNODE}>{self.NODE_ID_KEY}",
                                 'SN01')
        self._consumer_id = Conf.get(SSPL_CONF,
                                     f"{self.PROCESSOR}>{self.CONSUMER_ID}",
                                     'sspl_actuator')
        self._consumer_group = socket.gethostname()
        self._message_type = Conf.get(SSPL_CONF,
                                      f"{self.PROCESSOR}>{self.MESSAGE_TYPE}",
                                      'requests')
        self._offset = Conf.get(SSPL_CONF,
                                f"{self.PROCESSOR}>{self.OFFSET}",
                                'earliest')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        # TODO: cleanup message bus connection if that
        # functionality get added in messaging framework
        super(IngressProcessor, self).shutdown()
