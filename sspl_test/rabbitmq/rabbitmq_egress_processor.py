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
  Description:       Handles outgoing messages via rabbitMQ over localhost
 ****************************************************************************
"""

import json
import pika
import os
import time
from sspl_test.framework.base.module_thread import ScheduledModuleThread
from sspl_test.framework.base.internal_msgQ import InternalMsgQ
from sspl_test.framework.utils.service_logging import logger
from sspl_test.framework.utils import encryptor
from sspl_test.framework.base.sspl_constants import ServiceTypes
from .rabbitmq_sspl_test_connector import RabbitMQSafeConnection

import ctypes
try:
    use_security_lib=True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info("RabbitMQegressProcessor, libsspl_sec not found, disabling authentication on egress msgs")
    use_security_lib=False


class RabbitMQegressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles outgoing messages via rabbitMQ over localhost"""

    MODULE_NAME = "RabbitMQegressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    RACK_ID = "rack_id"
    NODE_ID = "node_id"
    CLUSTER_ID = "cluster_id"
    SITE_ID = "site_id"

    RABBITMQPROCESSOR       = MODULE_NAME.upper()
    VIRT_HOST               = 'virtual_host'

    PRIMARY_RABBITMQ_HOST   = 'primary_rabbitmq_host'
    EXCHANGE_NAME           = 'exchange_name'
    QUEUE_NAME              = 'queue_name'
    ROUTING_KEY             = 'routing_key'

    ACK_QUEUE_NAME          = 'ack_queue_name'
    ACK_ROUTING_KEY         = 'ack_routing_key'

    USER_NAME               = 'username'
    PASSWORD                = 'password'
    SIGNATURE_USERNAME      = 'message_signature_username'
    SIGNATURE_TOKEN         = 'message_signature_token'
    SIGNATURE_EXPIRES       = 'message_signature_expires'
    IEM_ROUTE_ADDR          = 'iem_route_addr'
    IEM_ROUTE_EXCHANGE_NAME = 'iem_route_exchange_name'

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RabbitMQegressProcessor.MODULE_NAME

    def __init__(self):
        super(RabbitMQegressProcessor, self).__init__(self.MODULE_NAME,
                                                      self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(RabbitMQegressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RabbitMQegressProcessor, self).initialize_msgQ(msgQlist)

        # Flag denoting that a shutdown message has been placed
        #  into our message queue from the main sspl_ll_d handler
        self._request_shutdown = False

        self._msg_sent_succesfull = True

        self._product = product

        # Configure RabbitMQ Exchange to transmit messages
        self._connection = None
        self._read_config()
        self._connection = RabbitMQSafeConnection(
            self._username, self._password, self._virtual_host,
            self._exchange_name, self._routing_key, self._queue_name
        )
        self._ack_connection = RabbitMQSafeConnection(
            self._username, self._password, self._virtual_host,
            self._exchange_name, self._ack_routing_key, self._ack_queue_name
        )
        self._iem_connection = RabbitMQSafeConnection(
            self._username, self._password, self._virtual_host,
            self._iem_route_exchange_name, self._routing_key,
            self._queue_name
        )
        # Display values used to configure pika from the config file
        self._log_debug("RabbitMQ user: %s" % self._username)
        self._log_debug("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                       (self._exchange_name, self._routing_key, self._virtual_host))

    def run(self):
        """Run the module periodically on its own thread. """
        self._log_debug("Start accepting requests")

        #self._set_debug(True)
        #self._set_debug_persist(True)

        try:
            # Loop thru all messages in queue until and transmit
            while not self._is_my_msgQ_empty():
                # Only get a new msg if we've successfully processed the current one
                if self._msg_sent_succesfull:
                    self._jsonMsg = self._read_my_msgQ()

                if self._jsonMsg is not None:
                    self._transmit_msg_on_exchange()

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.exception("RabbitMQegressProcessor restarting")

            # Configure RabbitMQ Exchange to receive messages
            self._get_connection()
            self._get_ack_connection()

        self._log_debug("Finished processing successfully")

        # Shutdown is requested by the sspl_ll_d shutdown handler
        #  placing a 'shutdown' msg into our queue which allows us to
        #  finish processing any other queued up messages.
        if self._request_shutdown == True:
            self.shutdown()
        else:
            self._scheduler.enter(1, self._priority, self.run, ())

    def _read_config(self):
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')

            # Read common RabbitMQ configuration
            self._primary_rabbitmq_host = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PRIMARY_RABBITMQ_HOST,
                                                                 'localhost')

            # Read RabbitMQ configuration for sensor messages
            self._queue_name    = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.QUEUE_NAME,
                                                                 'sensor-queue')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl-out')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ROUTING_KEY,
                                                                 'sensor-key')
            # Read RabbitMQ configuration for Ack messages
            self._ack_queue_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ACK_QUEUE_NAME,
                                                                 'sensor-queue')
            self._ack_routing_key = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ACK_ROUTING_KEY,
                                                                 'sensor-key')

            self._username      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PASSWORD,
                                                                 'sspl4ever')
            self._signature_user = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_USERNAME,
                                                                 'sspl-ll')
            self._signature_token = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_TOKEN,
                                                                 'FAKETOKEN1234')
            self._signature_expires = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_EXPIRES,
                                                                 "3600")
            self._iem_route_addr = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.IEM_ROUTE_ADDR,
                                                                 '')
            self._iem_route_exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.IEM_ROUTE_EXCHANGE_NAME,
                                                                 'sspl-in')
            self._rack_id = self._conf_reader._get_value_with_default(
                self.SYSTEM_INFORMATION, self.RACK_ID, '')

            self._node_id = self._conf_reader._get_value_with_default(
                self.SYSTEM_INFORMATION, self.NODE_ID, '')

            self._cluster_id = self._conf_reader._get_value_with_default(
                self.SYSTEM_INFORMATION, self.CLUSTER_ID, '')

            self._site_id = self._conf_reader._get_value_with_default(
                self.SYSTEM_INFORMATION, self.SITE_ID, '')

            # Decrypt RabbitMQ Password
            decryption_key = encryptor.gen_key(self._cluster_id, ServiceTypes.RABBITMQ.value)
            self._password = encryptor.decrypt(decryption_key, self._password.encode('ascii'), "RabbitMQegressProcessor")

            if self._iem_route_addr != "":
                logger.info("         Routing IEMs to host: %s" % self._iem_route_addr)
                logger.info("         Using IEM exchange: %s" % self._iem_route_exchange_name)
        except Exception as ex:
            logger.exception("RabbitMQegressProcessor, _read_config: %r" % ex)
            raise

    def _add_signature(self):
        """Adds the authentication signature to the message"""
        self._log_debug("_add_signature, jsonMsg: %s" % self._jsonMsg)
        self._jsonMsg["username"] = self._signature_user
        self._jsonMsg["expires"]  = int(self._signature_expires)
        self._jsonMsg["time"]     = str(int(time.time()))

        if use_security_lib:
            authn_token_len = len(self._signature_token) + 1
            session_length  = int(self._signature_expires)
            token = ctypes.create_string_buffer(SSPL_SEC.sspl_get_token_length())

            SSPL_SEC.sspl_generate_session_token(
                                    self._signature_user, authn_token_len,
                                    self._signature_token, session_length, token)

            # Generate the signature
            msg_len = len(self._jsonMsg) + 1
            sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
            SSPL_SEC.sspl_sign_message(msg_len, str(self._jsonMsg), self._signature_user,
                                       token, sig)

            self._jsonMsg["signature"] = str(sig.raw)
        else:
            self._jsonMsg["signature"] = "SecurityLibNotInstalled"

    def _transmit_msg_on_exchange(self):
        """Transmit json message onto RabbitMQ exchange"""
        self._log_debug("_transmit_msg_on_exchange, jsonMsg: %s" % self._jsonMsg)

        try:
            # Check for shut down message from sspl_ll_d and set a flag to shutdown
            #  once our message queue is empty
            if self._jsonMsg.get("message").get("actuator_response_type") is not None and \
                self._jsonMsg.get("message").get("actuator_response_type").get("thread_controller") is not None and \
                self._jsonMsg.get("message").get("actuator_response_type").get("thread_controller").get("thread_response") == \
                    "SSPL-LL is shutting down":
                    logger.info("RabbitMQegressProcessor, _transmit_msg_on_exchange, received" \
                                    "global shutdown message from sspl_ll_d")
                    self._request_shutdown = True

            msg_props = pika.BasicProperties()
            msg_props.content_type = "text/plain"

            # Publish json message to the correct channel
            # NOTE: We need to route ThreadController messages to ACK channel.
            # We can't modify schema as it will affect other modules too. As a
            # temporary solution we have added a extra check to see if actuator_response_type
            # is "thread_controller".
            # TODO: Find a proper way to solve this issue. Avoid changing
            # core egress processor code
            if self._jsonMsg.get("message").get("actuator_response_type") is not None and \
              (self._jsonMsg.get("message").get("actuator_response_type").get("ack") is not None or \
                self._jsonMsg.get("message").get("actuator_response_type").get("thread_controller") is not None):
                self._add_signature()
                jsonMsg = json.dumps(self._jsonMsg).encode('utf8')
                self._ack_connection.publish(exchange=self._exchange_name,
                                             routing_key=self._ack_routing_key,
                                             properties=msg_props,
                                             body=jsonMsg)
            # Routing requests for IEM msgs sent from the LoggingMsgHandler
            elif self._jsonMsg.get("message").get("IEM_routing") is not None:
                log_msg = self._jsonMsg.get("message").get("IEM_routing").get("log_msg")
                self._log_debug("Routing IEM: %s" % log_msg)
                if self._iem_route_addr != "":
                    self._iem_connection.publish(exchange=self._iem_route_exchange_name,
                                                 routing_key=self._routing_key,
                                                 properties=msg_props,
                                                 body=str(log_msg))
                else:
                    logger.warn("RabbitMQegressProcessor, Attempted to route IEM without a valid 'iem_route_addr' set.")

            elif self._jsonMsg.get("message") is not None:
                message = self._jsonMsg.get("message")
                if message.get("actuator_request_type") or \
                    message.get("sensor_request_type") is not None:
                    logger.error("inside egress, test actuator")
                    unique_routing_key = f'{self._routing_key}_node{self._node_id}'
                    logger.info(f"Connecting using routing key: {unique_routing_key}")
                    logger.error(f"Connecting using routing key: {unique_routing_key}")
                    self._add_signature()
                    jsonMsg = json.dumps(self._jsonMsg).encode('utf8')
                    self._connection.publish(exchange=self._exchange_name,
                                            routing_key=unique_routing_key,
                                            properties=msg_props,
                                            body=jsonMsg)

            else:
                self._add_signature()
                jsonMsg = json.dumps(self._jsonMsg).encode('utf8')
                self._connection.publish(exchange=self._exchange_name,
                                         routing_key=self._routing_key,
                                         properties=msg_props,
                                         body=jsonMsg)
            # No exceptions thrown so success
            self._log_debug("_transmit_msg_on_exchange, Successfully Sent: %s" % self._jsonMsg)
            self._msg_sent_succesfull = True

        except Exception as ex:
            logger.exception("RabbitMQegressProcessor, _transmit_msg_on_exchange: %r" % ex)
            self._msg_sent_succesfull = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQegressProcessor, self).shutdown()
