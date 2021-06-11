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
  Description:       Handles incoming messages via rabbitMQ for automated tests
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
from framework.base.sspl_constants import RESOURCE_PATH

import ctypes
SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')


class RabbitMQingressProcessorTests(ScheduledModuleThread, InternalMsgQ):
    """Handles incoming messages via rabbitMQ for automated tests"""

    MODULE_NAME = "RabbitMQingressProcessorTests"
    PRIORITY    = 1

    # Section and keys in configuration file
    RABBITMQPROCESSORTEST = MODULE_NAME.upper()
    PRIMARY_RABBITMQ_HOST = 'primary_rabbitmq_host'
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
        fileName = os.path.join(RESOURCE_PATH + '/actuators',
                                self.JSON_ACTUATOR_SCHEMA)

        with open(fileName, 'r') as f:
            _schema = f.read()

        # Remove tabs and newlines
        self._actuator_schema = json.loads(' '.join(_schema.split()))

        # Validate the schema
        Draft3Validator.check_schema(self._actuator_schema)

        # Read in the sensor schema for validating messages
        fileName = os.path.join(RESOURCE_PATH + '/sensors',
                                self.JSON_SENSOR_SCHEMA)

        with open(fileName, 'r') as f:
            _schema = f.read()

        # Remove tabs and newlines
        self._sensor_schema = json.loads(' '.join(_schema.split()))

        # Validate the schema
        Draft3Validator.check_schema(self._sensor_schema)


    def initialize(self, conf_reader, msgQlist, product):
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

            # Get the message type
            msgType = message.get("actuator_response_type")

            # If it's an incoming actuator msg then validate against
            #  Actuator Response schema
            if msgType is not None:
                validate(ingressMsg, self._actuator_schema)

            if msgType is None:
                msgType = message.get("sensor_response_type")
                validate(ingressMsg, self._sensor_schema)

                # Ignore drive status messages when thread starts up during tests
                if message.get("sensor_response_type").get("disk_status_drivemanager") is not None:
                    return

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
            self._primary_rabbitmq_host = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.PRIMARY_RABBITMQ_HOST,
                                                                 'localhost')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl-in')
            self._queue_name    = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.QUEUE_NAME,
                                                                 'actuator-req-queue')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSORTEST,
                                                                 self.ROUTING_KEY,
                                                                 'actuator-req-key')
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
                    host=self._primary_rabbitmq_host,
                    virtual_host=self._virtual_host,
                    credentials=creds
                    )
                )
            self._channel = self._connection.channel()
            self._channel.queue_declare(
                queue=self._queue_name,
                durable=True
                )
            self._channel.exchange_declare(
                exchange=self._exchange_name,
                exchange_type='topic',
                durable=True
                )
            self._channel.queue_bind(
                queue=self._queue_name,
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
