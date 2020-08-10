"""
 ****************************************************************************
 Filename:          ingress_processor.py
 Description:       Handles outgoing messages via amqp based message brokers
 Creation Date:     02/11/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import ctypes
import json
import os
import time

import pika
from eos.utils.amqp import AmqpConnectionError
from jsonschema import Draft3Validator, validate

from framework.amqp.egress_processor import EgressProcessor
from framework.amqp.utils import get_amqp_config
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.base.sspl_constants import COMMON_CONFIGS, RESOURCE_PATH
                                           
from framework.utils.amqp_factory import amqp_factory
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.ack_response import AckResponseMsg

try:
    use_security_lib = True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info(
        "libsspl_sec not found, disabling authentication on ingress msgs")
    use_security_lib = False


class IngressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles incoming messages via amqp"""

    MODULE_NAME = "IngressProcessor"
    PRIORITY = 1

    # Section and keys in configuration file
    AMQPPROCESSOR = MODULE_NAME.upper()
    EXCHANGE_NAME = 'exchange_name'
    QUEUE_NAME = 'queue_name'
    ROUTING_KEY = 'routing_key'
    VIRT_HOST = 'virtual_host'

    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
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
        # dir = os.path.dirname(__file__)
        #schema_file = os.path.join(dir, '..', '..', 'json_msgs',
        #                           'schemas', 'actuators',
        #                           self.JSON_ACTUATOR_SCHEMA)
        schema_file = os.path.join(RESOURCE_PATH + '/actuators',
                                   self.JSON_ACTUATOR_SCHEMA)
        self._actuator_schema = self._load_schema(schema_file)

        # Read in the sensor schema for validating messages
        #schema_file = os.path.join(dir, '..', '..', 'json_msgs',
        #                           'schemas', 'sensors',
        #                           self.JSON_SENSOR_SCHEMA)
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

        amqp_config = get_amqp_config(section=self.AMQPPROCESSOR, 
                    keys=[(self.VIRT_HOST, "SSPL"), (self.EXCHANGE_NAME, "sspl-in"), 
                    (self.QUEUE_NAME, "sensor-queue"), (self.ROUTING_KEY, "actuator-req-queue")])
        self._comm = amqp_factory.get_amqp_consumer(**amqp_config)
        try:
            self._comm.init()
        except AmqpConnectionError:
            logger.error(f"{self.MODULE_NAME} amqp connection is not initialized")

    def run(self):
        # self._set_debug(True)
        # self._set_debug_persist(True)

        #time.sleep(180)
        logger.info(f"{self.MODULE_NAME}, Initialization complete, accepting requests")

        try:
            self._comm.recv(callback_fn=self._process_msg)
        except Exception as e:
            if self.is_running() is True:
                logger.info(f"{self.MODULE_NAME} ungracefully breaking out of run loop, restarting.")
                logger.error(f"{self.MODULE_NAME}, Exception: {e}")
                self._scheduler.enter(10, self._priority, self.run, ())
            else:
                logger.info(f"{self.MODULE_NAME} gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, body):
        """Parses the incoming message and hands off to the appropriate module"""

        ingressMsg = {}
        uuid = None
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
               SSPL_SEC.sspl_verify_message(msg_len, str(message), username, signature) != 0:
                logger.warn(f"{self.MODULE_NAME}, Authentication failed on message: {ingressMsg}")
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

            # Hand off to appropriate actuator message handler
            if msgType.get("logging") is not None:
                self._write_internal_msgQ("LoggingMsgHandler", message)

            elif msgType.get("thread_controller") is not None:
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
                ack_msg = AckResponseMsg("Error Processing Message", "Message Handler Not Found", uuid).getJson()
                self._write_internal_msgQ(EgressProcessor.name(), ack_msg)

            # Acknowledge message was received
            self._comm.acknowledge()

        except Exception as ex:
            logger.error(f"{self.MODULE_NAME}, _process_msg unrecognized message: {ingressMsg}")
            ack_msg = AckResponseMsg("Error Processing Msg", "Msg Handler Not Found", uuid).getJson()
            self._write_internal_msgQ(EgressProcessor.name(), ack_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(IngressProcessor, self).shutdown()
        try:
            self._comm.stop()
        except pika.exceptions.ConnectionClosed:
            logger.info(f"{self.MODULE_NAME}, shutdown, amqp ConnectionClosed")
        except Exception as err:
            logger.info(f"{self.MODULE_NAME}, shutdown, amqp {err}")
