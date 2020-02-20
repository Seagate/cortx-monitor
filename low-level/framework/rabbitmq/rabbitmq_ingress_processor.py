"""
 ****************************************************************************
 Filename:          rabbitmq_ingress_processor.py
 Description:       Handles incoming messages via rabbitMQ
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

from jsonschema import Draft3Validator
from jsonschema import validate
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from json_msgs.messages.actuators.ack_response import AckResponseMsg
from framework.base.sspl_constants import RESOURCE_PATH

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

        self._virtual_host = None
        self._queue_name = None
        self._routing_key = None
        self._username = None
        self._connection = None
        self._primary_rabbitmq_host = None
        self._exchange_name = None
        self._password = None
        self._channel = None

        self._wait_time = 10

    def _load_schema(self, schema_file):
        """Loads a schema from a file and validates

        @param string schema_file     location of schema on the file system
        @return string                Trimmed and validated schema
        """
        with open(schema_file, 'r') as f:
            schema = f.read()

        # Remove tabs and newlines
        schema_trimmed = json.loads(' '.join(schema.split()))

        # Validate the schema to conform to Draft 3 specification
        Draft3Validator.check_schema(schema_trimmed)

        return schema_trimmed

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

        time.sleep(180)
        logger.info("RabbitMQingressProcessor, Initialization complete, accepting requests")

        try:
            result = self._channel.queue_declare(queue="", exclusive=True)
            self._channel.queue_bind(exchange=self._exchange_name,
                               queue=result.method.queue,
                               routing_key=self._routing_key)
            self._channel.basic_consume(on_message_callback=self._process_msg, queue=result.method.queue)
            self._channel.start_consuming()

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
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as ex:
            logger.error("RabbitMQingressProcessor, _process_msg unrecognized message: %r" % ingressMsg)
            ack_msg = AckResponseMsg("Error Processing Msg", "Msg Handler Not Found", uuid).getJson()
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), ack_msg)

    def _configure_exchange(self, retry=False):
        """Configure the RabbitMQ exchange with defaults available"""
        # Make methods locally available
        get_value_with_default = self._conf_reader._get_value_with_default
        try:

            self._virtual_host = get_value_with_default(self.RABBITMQPROCESSOR,
                                                        self.VIRT_HOST, 'SSPL')

            self._primary_rabbitmq_host = get_value_with_default(
                self.RABBITMQPROCESSOR, self.PRIMARY_RABBITMQ_HOST,
                'localhost')

            self._exchange_name = get_value_with_default(
                self.RABBITMQPROCESSOR, self.EXCHANGE_NAME, 'sspl-in')

            self._queue_name = get_value_with_default(
                self.RABBITMQPROCESSOR, self.QUEUE_NAME, 'actuator-req-queue')

            self._routing_key = get_value_with_default(
                self.RABBITMQPROCESSOR, self.ROUTING_KEY, 'actuator-req-key')

            self._username = get_value_with_default(self.RABBITMQPROCESSOR,
                                                    self.USER_NAME,
                                                    'sspluser')

            self._password = get_value_with_default(self.RABBITMQPROCESSOR,
                                                    self.PASSWORD,
                                                    'sspl4ever')

            # Ensure the rabbitmq queues/etc exist
            creds = pika.PlainCredentials(self._username, self._password)
            self._connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=self._primary_rabbitmq_host,
                    virtual_host=self._virtual_host,
                    credentials=creds
                    )
                )
            self._channel = self._connection.channel()
            try:
                self._channel.queue_declare(queue=self._queue_name, durable=True)
            except Exception as e:
                logger.error(e)
            try:
                self._channel.exchange_declare(
                    exchange=self._exchange_name,
                    exchange_type='topic',
                    durable=True
                    )
            except Exception as e:
                logger.error(e)
            self._channel.queue_bind(
                queue=self._queue_name,
                exchange=self._exchange_name,
                routing_key=self._routing_key
                )
        except Exception as ex:
            logger.error("RabbitMQingressProcessor, \
                _configure_exchange: %r" % ex)
            if retry:
                time.sleep(self._wait_time)
                self._configure_exchange(retry=True)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQingressProcessor, self).shutdown()
        try:
            self._connection.close()
            self._channel.stop_consuming()
        except pika.exceptions.ConnectionClosed:
            logger.info("RabbitMQingressProcessor, shutdown, \
                RabbitMQ ConnectionClosed")
