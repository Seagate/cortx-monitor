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
import time
import socket

from jsonschema import Draft3Validator
from jsonschema import validate

from pika import exceptions
from sspl_test.framework.base.module_thread import ScheduledModuleThread
from sspl_test.framework.base.internal_msgQ import InternalMsgQ
from sspl_test.framework.utils.service_logging import logger
from sspl_test.framework.base.sspl_constants import RESOURCE_PATH
from sspl_test.framework.utils import encryptor
from sspl_test.framework.base.sspl_constants import ServiceTypes
from .rabbitmq_sspl_test_connector import RabbitMQSafeConnection
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

    SYSTEM_INFORMATION_KEY = "SYSTEM_INFORMATION"
    CLUSTER_ID_KEY = "cluster_id"

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
        #fileName = os.path.join(dir, '..', '..', 'low-level', 'json_msgs',
        #                        'schemas', 'actuators',
        #                        self.JSON_ACTUATOR_SCHEMA)
        fileName = os.path.join(RESOURCE_PATH + '/actuators',
                                self.JSON_ACTUATOR_SCHEMA)

        self._actuator_schema = self._load_schema(fileName)

        # Read in the sensor schema for validating messages
        dir = os.path.dirname(__file__)
        #fileName = os.path.join(dir, '..', '..', 'low-level', 'json_msgs',
        #                        'schemas', 'sensors',
        #                        self.JSON_SENSOR_SCHEMA)
        fileName = os.path.join(RESOURCE_PATH + '/sensors',
                                self.JSON_SENSOR_SCHEMA)

        self._sensor_schema = self._load_schema(fileName)

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
            self._connection.consume(callback=self._process_msg)
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
            # If the message comes from other SSPL hosts, do not pass that
            # message to internal queue. This happens as SSPL instances are
            # listening to common queues in a RabbitMQ cluster.
            if 'host_id' in msgType and socket.getfqdn() != msgType['host_id']:
                self._connection.ack(ch, delivery_tag=method.delivery_tag)
                return
            # Write to the msg queue so the lettuce tests can
            #  retrieve it and examine for accuracy during automated testing
            self._write_internal_msgQ("RabbitMQingressProcessorTests", message)

            # Acknowledge message was received
            self._connection.ack(ch, delivery_tag=method.delivery_tag)

        except Exception as ex:
            logger.exception("_process_msg unrecognized message: %r" % ingressMsg)

    def _configure_exchange(self):
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host = self._conf_reader._get_value_with_default(
                self.RABBITMQPROCESSORTEST, self.VIRT_HOST, "SSPL"
            )
            self._primary_rabbitmq_host = self._conf_reader._get_value_with_default(
                self.RABBITMQPROCESSORTEST, self.PRIMARY_RABBITMQ_HOST, "localhost"
            )
            self._exchange_name = self._conf_reader._get_value_with_default(
                self.RABBITMQPROCESSORTEST, self.EXCHANGE_NAME, "sspl-in"
            )
            self._queue_name = self._conf_reader._get_value_with_default(
                self.RABBITMQPROCESSORTEST, self.QUEUE_NAME, "actuator-req-queue"
            )
            self._routing_key = self._conf_reader._get_value_with_default(
                self.RABBITMQPROCESSORTEST, self.ROUTING_KEY, "actuator-req-key"
            )
            self._username = self._conf_reader._get_value_with_default(
                self.RABBITMQPROCESSORTEST, self.USER_NAME, "sspluser"
            )
            self._password = self._conf_reader._get_value_with_default(
                self.RABBITMQPROCESSORTEST, self.PASSWORD, "sspl4ever"
            )
            self._connection = RabbitMQSafeConnection(
                self._username,
                self._password,
                self._virtual_host,
                self._exchange_name,
                self._routing_key,
                self._queue_name
            )
            self.cluster_id = self._conf_reader._get_value_with_default(
                self.SYSTEM_INFORMATION_KEY, self.CLUSTER_ID_KEY, '')
            # Decrypt RabbitMQ Password
            decryption_key = encryptor.gen_key(self.cluster_id, ServiceTypes.RABBITMQ.value)
            self._password = encryptor.decrypt(decryption_key, self._password.encode('ascii'), "RabbitMQingressProcessor")
        except Exception as ex:
            logger.exception("_configure_exchange: %r" % ex)
            raise

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQingressProcessorTests, self).shutdown()
        time.sleep(4)
        try:
            self._connection.cleanup()
        except pika.exceptions.ConnectionClosed:
            logger.info("RabbitMQingressProcessorTests, shutdown, RabbitMQ ConnectionClosed")
        except Exception as err:
            logger.info("RabbitMQingressProcessorTests, shutdown, RabbitMQ {}".format(str(err)))

