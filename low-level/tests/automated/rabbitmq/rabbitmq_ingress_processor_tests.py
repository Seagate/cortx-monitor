"""
 ****************************************************************************
 Filename:          rabbitmq_ingress_processor_test.py
 Description:       Handles incoming messages via rabbitMQ for automated tests
 Creation Date:     03/16/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import pika
import json
import os

from jsonschema import Draft3Validator
from jsonschema import validate
from lettuce import *

from pika import exceptions

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Import message handlers to hand off messages
from message_handlers.logging_msg_handler import LoggingMsgHandler

import ctypes
SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')


class RabbitMQingressProcessorTests(ScheduledModuleThread, InternalMsgQ):
    """Handles incoming messages via rabbitMQ for automated tests"""

    MODULE_NAME = "RabbitMQingressProcessorTests"
    PRIORITY    = 1

    # Section and keys in configuration file
    RABBITMQPROCESSORTEST = MODULE_NAME.upper()
    EXCHANGE_NAME         = 'exchange_name'
    QUEUE_NAME            = 'queue_name'
    ROUTING_KEY           = 'routing_key'
    VIRT_HOST             = 'virtual_host'
    USER_NAME             = 'username'
    PASSWORD              = 'password'

    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Response.json"
    JSON_SENSOR_SCHEMA   = "SSPL-LL_Sensor_Response.json"


    @staticmethod
    def name():
        """ @return: name of the module."""
        return RabbitMQingressProcessorTests.MODULE_NAME

    def __init__(self):
        super(RabbitMQingressProcessorTests, self).__init__(self.MODULE_NAME,
                                                       self.PRIORITY)

        # Read in the actuator schema for validating messages
        dir = os.path.dirname(__file__)
        fileName = os.path.join(dir, '..', '..', '..', 'json_msgs',
                                'schemas', 'actuators',
                                self.JSON_ACTUATOR_SCHEMA)

        with open(fileName, 'r') as f:
            _schema = f.read()

        # Remove tabs and newlines
        self._actuator_schema = json.loads(' '.join(_schema.split()))

        # Validate the schema
        Draft3Validator.check_schema(self._actuator_schema)

        # Read in the sensor schema for validating messages
        dir = os.path.dirname(__file__)
        fileName = os.path.join(dir, '..', '..', '..', 'json_msgs',
                                'schemas', 'sensors',
                                self.JSON_SENSOR_SCHEMA)

        with open(fileName, 'r') as f:
            _schema = f.read()

        # Remove tabs and newlines
        self._sensor_schema = json.loads(' '.join(_schema.split()))

        # Validate the schema
        Draft3Validator.check_schema(self._sensor_schema)


    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(RabbitMQingressProcessorTests, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RabbitMQingressProcessorTests, self).initialize_msgQ(msgQlist)

        # Configure RabbitMQ Exchange to receive messages
        self._configure_exchange()

        # Display values used to configure pika from the config file
        self._log_debug("RabbitMQ user: %s" % self._username)
        self._log_debug("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                      (self._exchange_name, self._routing_key, self._virtual_host))

    def run(self):
        """Run the module periodically on its own thread. """
        self._log_debug("Start accepting requests")

        try:
            result = self._channel.queue_declare(exclusive=True)
            self._channel.queue_bind(exchange=self._exchange_name,
                               queue=result.method.queue,
                               routing_key=self._routing_key)

            self._channel.basic_consume(self._process_msg,
                                  queue=result.method.queue)
            self._channel.start_consuming()

        except Exception:
            if self.is_running() == True:
                logger.info("RabbitMQingressProcessorTests ungracefully breaking out of run loop, restarting.")

                # Configure RabbitMQ Exchange to receive messages
                self._configure_exchange()
                self._scheduler.enter(1, self._priority, self.run, ())
            else:
                logger.info("RabbitMQingressProcessorTests gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, ch, method, properties, body):
        """Parses the incoming message and hands off to the appropriate module"""

        self._log_debug("_process_msg, body: %s" % body)

        ingressMsg = {}
        try:
            if isinstance(body, dict) == False:
                ingressMsg = json.loads(body)
            else:
                ingressMsg = body

            # Authenticate message using username and signature fields
            username  = ingressMsg.get("username")
            signature = ingressMsg.get("signature")
            message   = ingressMsg.get("message")
            
            assert(username is not None)
            assert(signature is not None)
            assert(message is not None)
            
            msg_len   = len(message) + 1

            if SSPL_SEC.sspl_verify_message(msg_len, str(message), username, signature) != 0:
                logger.error("Authentication failed on message: %s" % ingressMsg)
                return

            # We're acting as HAlon so ignore actuator_requests
            #  and sensor_requests messages
            if message.get("actuator_request_type") is not None or \
                message.get("sensor_request_type") is not None:
                return

            # Get the message type which 
            msgType = message.get("actuator_response_type")

            # If it's an incoming actuator msg then validate against
            #  Actuator Response schema
            if msgType is not None:
                validate(ingressMsg, self._actuator_schema)

            if msgType is None:
                msgType = message.get("sensor_response_type")
                validate(ingressMsg, self._sensor_schema)

            # Write to the msg queue so the lettuce tests can
            #  retrieve it and examine for accuracy during automated testing
            self._write_internal_msgQ("RabbitMQingressProcessorTests", message)            

            # Acknowledge message was received
            ch.basic_ack(delivery_tag = method.delivery_tag)

        except Exception as ex:
            logger.exception("_process_msg unrecognized message: %r" % ingressMsg)


    def _configure_exchange(self):
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl_halon')
            self._queue_name    = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.QUEUE_NAME,
                                                                 'SSPL-LL')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.ROUTING_KEY,
                                                                 'sspl_ll')
            self._username      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.PASSWORD,
                                                                 'sspl4ever')
            # ensure the rabbitmq queues/etc exist
            creds = pika.PlainCredentials(self._username, self._password)
            self._connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    virtual_host=self._virtual_host,
                    credentials=creds
                    )
                )
            self._channel = self._connection.channel()
            self._channel.queue_declare(
                queue='SSPL-LL',
                durable=False
                )
            self._channel.exchange_declare(
                exchange=self._exchange_name,
                exchange_type='topic',
                durable=False
                )
            self._channel.queue_bind(
                queue='SSPL-LL',
                exchange=self._exchange_name,
                routing_key=self._routing_key
                )
        except Exception as ex:
            logger.exception("_configure_exchange: %r" % ex)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQingressProcessorTests, self).shutdown()
        try:
            if self._connection is not None:
                self._connection.close()
            self._channel.stop_consuming()
        except pika.exceptions.ConnectionClosed:
            logger.info("RabbitMQingressProcessorTests, shutdown, RabbitMQ ConnectionClosed")