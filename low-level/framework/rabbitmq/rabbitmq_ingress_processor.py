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

from cortx.utils.security.cipher import Cipher
import pika

from jsonschema import Draft3Validator
from jsonschema import validate
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from .rabbitmq_connector import RabbitMQSafeConnection
from framework.utils import encryptor
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from json_msgs.messages.actuators.ack_response import AckResponseMsg
from framework.base.sspl_constants import RESOURCE_PATH, ServiceTypes, COMMON_CONFIGS
from framework.utils.conf_utils import *


try:
    use_security_lib = True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info(
        "libsspl_sec not found, disabling authentication on ingress msgs")
    use_security_lib = False


class RabbitMQingressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles incoming messages via rabbitMQ"""

    MODULE_NAME = "RabbitMQingressProcessor"
    PRIORITY = 1

    # Section and keys in configuration file
    RABBITMQPROCESSOR = MODULE_NAME.upper()
    PRIMARY_RABBITMQ_HOST = 'primary_rabbitmq_host'
    EXCHANGE_NAME = 'exchange_name'
    QUEUE_NAME = 'queue_name'
    ROUTING_KEY = 'routing_key'
    VIRT_HOST = 'virtual_host'
    USER_NAME = 'username'
    PASSWORD = 'password'

    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
    CLUSTER_ID_KEY = 'cluster_id'
    NODE_ID_KEY = 'node_id'

    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Request.json"
    JSON_SENSOR_SCHEMA = "SSPL-LL_Sensor_Request.json"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RabbitMQingressProcessor.MODULE_NAME

    def __init__(self):
        super(RabbitMQingressProcessor, self).__init__(self.MODULE_NAME,
                                                       self.PRIORITY)

        # Read in the actuator schema for validating messages
        schema_file = os.path.join(RESOURCE_PATH + '/actuators',
                                   self.JSON_ACTUATOR_SCHEMA)
        self._actuator_schema = self._load_schema(schema_file)

        # Read in the sensor schema for validating messages
        schema_file = os.path.join(RESOURCE_PATH + '/sensors',
                                   self.JSON_SENSOR_SCHEMA)
        self._sensor_schema = self._load_schema(schema_file)

        self._virtual_host = None
        self._queue_name = None
        self._routing_key = None
        self._username = None
        self._connection = None
        self._primary_rabbitmq_host = None
        self._exchange_name = None
        self._password = None
        self._channel = None

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
        super(RabbitMQingressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RabbitMQingressProcessor, self).initialize_msgQ(msgQlist)

        # Configure RabbitMQ Exchange to receive messages
        self._configure_exchange(retry=False)

        # Display values used to configure pika from the config file
        self._log_debug("RabbitMQ user: %s" % self._username)
        self._log_debug("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                        (self._exchange_name, self._routing_key, self._virtual_host))

    def run(self):
        # self._set_debug(True)
        # self._set_debug_persist(True)

        #time.sleep(180)
        logger.info("RabbitMQingressProcessor, Initialization complete, accepting requests")

        try:
            self._connection.consume(callback=self._process_msg)
        except Exception as e:
            if self.is_running() is True:
                logger.info("RabbitMQingressProcessor ungracefully breaking out of run loop, restarting.")
                logger.error("RabbitMQingressProcessor, Exception: %s" % str(e))
                self._configure_exchange(retry=True)
                self._scheduler.enter(10, self._priority, self.run, ())
            else:
                logger.info("RabbitMQingressProcessor gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, ch, method, properties, body):
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
                logger.warn("RabbitMQingressProcessor, Authentication failed on message: %s" % ingressMsg)
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
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), ack_msg)

            # Acknowledge message was received
            self._connection.ack(ch, delivery_tag=method.delivery_tag)

        except Exception as ex:
            logger.error("RabbitMQingressProcessor, _process_msg unrecognized message: %r" % ingressMsg)
            ack_msg = AckResponseMsg("Error Processing Msg", "Msg Handler Not Found", uuid).getJson()
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), ack_msg)

    def _configure_exchange(self, retry=False):
        """Configure the RabbitMQ exchange with defaults available"""
        # Make methods locally available
        try:
            self._virtual_host  = Conf.get(SSPL_CONF, f"{self.RABBITMQPROCESSOR}>{self.VIRT_HOST}",
                                                            'SSPL')

            # Read common RabbitMQ configuration
            self._primary_rabbitmq_host = Conf.get(SSPL_CONF, f"{self.RABBITMQPROCESSOR}>{self.PRIMARY_RABBITMQ_HOST}",
                                                                 'localhost')

            # Read RabbitMQ configuration for sensor messages
            self._queue_name    = Conf.get(SSPL_CONF, f"{self.RABBITMQPROCESSOR}>{self.QUEUE_NAME}",
                                                                 'actuator-req-queue')
            self._exchange_name = Conf.get(SSPL_CONF, f"{self.RABBITMQPROCESSOR}>{self.EXCHANGE_NAME}",
                                                                 'sspl-in')
            self._routing_key   = Conf.get(SSPL_CONF, f"{self.RABBITMQPROCESSOR}>{self.ROUTING_KEY}",
                                                                 'actuator-req-key')
            self._username = Conf.get(SSPL_CONF, f"{self.RABBITMQPROCESSOR}>{self.USER_NAME}",
                                                                 'sspluser')
            self._password = Conf.get(SSPL_CONF, f"{self.RABBITMQPROCESSOR}>{self.PASSWORD}",'')
            
            cluster_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{self.CLUSTER_ID_KEY}",'001')
        
            node_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{self.NODE_ID_KEY}",'001')
            # Decrypt RabbitMQ Password
            decryption_key = encryptor.gen_key(cluster_id, ServiceTypes.RABBITMQ.value)
            self._password = encryptor.decrypt(decryption_key, self._password.encode('ascii'), "RabbitMQingressProcessor")

            # Create a routing key unique to this instance
            unique_routing_key = f'{self._routing_key}_node{node_id}'
            logger.info(f"Connecting using routing key: {unique_routing_key}")
            self._connection = RabbitMQSafeConnection(
                self._username, self._password, self._virtual_host,
                self._exchange_name, unique_routing_key, self._queue_name
            )
        except Exception as ex:
            logger.error("RabbitMQingressProcessor, _configure_exchange: %r" % ex)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQingressProcessor, self).shutdown()
        try:
            self._connection.cleanup()
        except pika.exceptions.ConnectionClosed:
            logger.info("RabbitMQingressProcessorTests, shutdown, RabbitMQ ConnectionClosed")
        except Exception as err:
            logger.info("RabbitMQingressProcessorTests, shutdown, RabbitMQ {}".format(str(err)))

