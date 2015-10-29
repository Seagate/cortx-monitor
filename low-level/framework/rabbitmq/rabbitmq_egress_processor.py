"""
 ****************************************************************************
 Filename:          rabbitmq_egress_processor.py
 Description:       Handles outgoing messages via rabbitMQ
 Creation Date:     01/14/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import datetime
import json
import pika
import os

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.thread_controller import ThreadControllerMsg

import ctypes
SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')


class RabbitMQegressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles outgoing messages via rabbitMQ"""

    MODULE_NAME = "RabbitMQegressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
    RABBITMQPROCESSOR   = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'
    ACK_EXCHANGE_NAME   = 'ack_exchange_name'
    ROUTING_KEY         = 'routing_key'
    VIRT_HOST           = 'virtual_host'
    USER_NAME           = 'username'
    PASSWORD            = 'password'
    SIGNATURE_USERNAME  = 'message_signature_username'
    SIGNATURE_TOKEN     = 'message_signature_token'
    SIGNATURE_EXPIRES   = 'message_signature_expires'

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RabbitMQegressProcessor.MODULE_NAME

    def __init__(self):
        super(RabbitMQegressProcessor, self).__init__(self.MODULE_NAME,
                                                      self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(RabbitMQegressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RabbitMQegressProcessor, self).initialize_msgQ(msgQlist)

        # Configure RabbitMQ Exchange to transmit message
        self._read_config()
        self._get_connection()

        # Flag denoting that a shutdown message has been placed
        #  into our message queue from the main sspl_ll_d handler
        self._request_shutdown = False

        # Display values used to configure pika from the config file
        self._log_debug("RabbitMQ user: %s" % self._username)
        self._log_debug("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                       (self._exchange_name, self._routing_key, self._virtual_host))

        self._signature_user = self._conf_reader._get_value_with_default(
                                                    self.RABBITMQPROCESSOR, 
                                                    self.SIGNATURE_USERNAME,
                                                    'sspl-ll')

        self._signature_token = self._conf_reader._get_value_with_default(
                                                    self.RABBITMQPROCESSOR, 
                                                    self.SIGNATURE_TOKEN,
                                                    'FAKETOKEN1234')

        self._signature_expires = self._conf_reader._get_value_with_default(
                                                    self.RABBITMQPROCESSOR, 
                                                    self.SIGNATURE_EXPIRES,
                                                    "3600")

    def run(self):
        """Run the module periodically on its own thread. """
        self._log_debug("Start accepting requests")

        #self._set_debug(True)
        #self._set_debug_persist(True)

        try:
            # Block on message queue until it contains an entry
            jsonMsg = self._read_my_msgQ()

            if jsonMsg is not None:
                self._add_signature(jsonMsg)
                self._transmit_msg_on_exchange(jsonMsg)
 
            # Loop thru all messages in queue until and transmit
            while not self._is_my_msgQ_empty():
                jsonMsg = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._add_signature(jsonMsg)
                    self._transmit_msg_on_exchange(jsonMsg)

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.exception("RabbitMQegressProcessor restarting")

            # Configure RabbitMQ Exchange to receive messages
            self._read_config()
            self._get_connection()

        self._log_debug("Finished processing successfully")

        # Shutdown is requested by the sspl_ll_d shutdown handler
        #  placing a 'shutdown' msg into our queue which allows us to
        #  finish processing any other queued up messages.
        if self._request_shutdown == True:
            self.shutdown()
        else:
            self._scheduler.enter(10, self._priority, self.run, ())

    def _read_config(self):
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl_halon')
            self._ack_exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ACK_EXCHANGE_NAME,
                                                                 'sspl_command_ack')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ROUTING_KEY,
                                                                 'sspl_ll')           
            self._username      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PASSWORD,
                                                                 'sspl4ever')
        except Exception as ex:
            logger.exception("_read_config: %r" % ex)

    def _get_connection(self):
        try:
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
            logger.exception("_get_connection: %r" % ex)

    def _get_ack_connection(self):
        try:
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
                exchange=self._ack_exchange_name,
                exchange_type='topic',
                durable=False
                )
            self._channel.queue_bind(
                queue='SSPL-LL',
                exchange=self._ack_exchange_name,
                routing_key=self._routing_key
                )
        except Exception as ex:
            logger.exception("_get_connection: %r" % ex)

    def _add_signature(self, jsonMsg):
        """Adds the authentication signature to the message"""
        self._log_debug("_add_signature, jsonMsg: %s" % jsonMsg)
        jsonMsg["username"] = self._signature_user
        jsonMsg["expires"]  = int(self._signature_expires)
        jsonMsg["time"]     = str(datetime.datetime.now())

        authn_token_len = len(self._signature_token) + 1
        session_length  = int(self._signature_expires)
        token = ctypes.create_string_buffer(SSPL_SEC.sspl_get_token_length())

        SSPL_SEC.sspl_generate_session_token(
                                self._signature_user, authn_token_len, 
                                self._signature_token, session_length, token)

        # Generate the signature
        msg_len = len(jsonMsg) + 1
        sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
        SSPL_SEC.sspl_sign_message(msg_len, str(jsonMsg), self._signature_user,
                                   token, sig)

        jsonMsg["signature"] = str(sig.raw)

    def _transmit_msg_on_exchange(self, jsonMsg):
        """Transmit json message onto RabbitMQ exchange"""
        self._log_debug("_transmit_msg_on_exchange, jsonMsg: %s" % jsonMsg)

        try:
            jsonMsg = json.dumps(jsonMsg).encode('utf8')

            msg_props = pika.BasicProperties()
            msg_props.content_type = "text/plain"

            # Publish json message to the correct channel
            if json.loads(jsonMsg).get("message").get("actuator_response_type") is not None and \
                json.loads(jsonMsg).get("message").get("actuator_response_type").get("ack") is not None:
                  self._get_ack_connection()
                  self._channel.basic_publish(exchange=self._ack_exchange_name,
                                    routing_key=self._routing_key,
                                    properties=msg_props,
                                    body=str(jsonMsg))
            else:
                self._get_connection()
                self._channel.basic_publish(exchange=self._exchange_name,
                                  routing_key=self._routing_key,
                                  properties=msg_props,
                                  body=str(jsonMsg))

            # No exceptions thrown so success
            self._log_debug("_transmit_msg_on_exchange, Successfully Sent: %s" % jsonMsg)
            self._connection.close()
            del(self._connection)

            # Check for shut down message from sspl_ll_d and set a flag to shutdown
            #  once our message queue is empty 
            if isinstance(jsonMsg, ThreadControllerMsg):
                if jsonMsg.get("actuator_response_type").get("thread_response") \
                                            == "SSPL-LL is shutting down":
                    self._log_debug("_transmit_msg_on_exchange, received" \
                                    "global shutdown message from sspl_ll_d")
                    self._request_shutdown = True

        except Exception as ex:
            logger.exception("_transmit_msg_on_exchange: %r" % ex)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQegressProcessor, self).shutdown()