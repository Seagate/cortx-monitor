"""
 ****************************************************************************
 Filename:          egress_processor.py
 Description:       Handles outgoing messages via rabbitMQ over localhost
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

import json
import pika
import time
import sys

from eos.utils.amqp import AmqpConnectionError
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.utils import encryptor
from framework.utils.store_factory import store
from framework.utils import mon_utils
from framework.utils.amqp_factory import amqp_factory
from framework.utils.store_queue import store_queue
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS

import ctypes
try:
    use_security_lib=True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info("EgressProcessor, libsspl_sec not found, disabling authentication on egress msgs")
    use_security_lib=False


class EgressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles outgoing messages via rabbitMQ over localhost"""

    MODULE_NAME = "EgressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
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

    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
    CLUSTER_ID_KEY = 'cluster_id'
    NODE_ID_KEY = 'node_id'
    RABBITMQ_CLUSTER_SECTION = 'RABBITMQCLUSTER'
    RABBITMQ_CLUSTER_HOSTS_KEY = 'cluster_nodes'

    @staticmethod
    def name():
        """ @return: name of the module."""
        return EgressProcessor.MODULE_NAME

    def __init__(self):
        super(EgressProcessor, self).__init__(self.MODULE_NAME,
                                                      self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(EgressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(EgressProcessor, self).initialize_msgQ(msgQlist)

        # Flag denoting that a shutdown message has been placed
        #  into our message queue from the main sspl_ll_d handler
        self._request_shutdown = False

        self._read_config()

        # Get common amqp config
        amqp_config = self._get_default_amqp_config()
        self._default_comm = amqp_factory.get_amqp_producer(**amqp_config)
        try:
            self._default_comm.init()
        except AmqpConnectionError:
            logger.warning(f"{self.MODULE_NAME} amqp connection is not initialized, \
                 messages will be stored in consul")

        # Update ack specific amqp config
        ack_amqp_config = {"exchange_queue" : self._ack_queue_name,
                           "routing_key": self._ack_routing_key}
        ack_amqp_config = {**amqp_config, **ack_amqp_config}
        self._ack_comm = amqp_factory.get_amqp_producer(**ack_amqp_config)
        try:
            self._ack_comm.init()
        except AmqpConnectionError:
            logger.warning(f"{self.MODULE_NAME} amqp connection is not initialized, \
                 messages will be stored in consul")

        # Update IEM specifc amqp config
        iem_amqp_config = {"exchange": self._iem_route_exchange_name}
        iem_amqp_config = {**amqp_config, **iem_amqp_config}
        self._iem_comm = amqp_factory.get_amqp_producer(**amqp_config)
        try:
            self._iem_comm.init()
        except AmqpConnectionError:
            logger.warning(f"{self.MODULE_NAME} amqp connection is not initialized, \
                 messages will be stored in consul")

    def run(self):
        """Run the module periodically on its own thread. """
        self._log_debug("Start accepting requests")

        try:
            # Loop thru all messages in queue until and transmit
            while not self._is_my_msgQ_empty():
                self._jsonMsg, self._event = self._read_my_msgQ()

                if self._jsonMsg is not None:
                    self._transmit_msg_on_exchange()

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.error(f"{self.MODULE_NAME} restarting")

        self._log_debug("Finished processing successfully")

        # Shutdown is requested by the sspl_ll_d shutdown handler
        #  placing a 'shutdown' msg into our queue which allows us to
        #  finish processing any other queued up messages.
        if self._request_shutdown is True:
            self.shutdown()
        else:
            self._scheduler.enter(1, self._priority, self.run, ())

    def _read_config(self):
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')

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

            self._username = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PASSWORD,
                                                                 '')
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
            self._hosts = self._conf_reader._get_value_list(self.RABBITMQ_CLUSTER_SECTION, 
                                COMMON_CONFIGS.get(self.RABBITMQ_CLUSTER_SECTION).get(self.RABBITMQ_CLUSTER_HOSTS_KEY))
            cluster_id = self._conf_reader._get_value_with_default(self.SYSTEM_INFORMATION_KEY,
                                                                   COMMON_CONFIGS.get(self.SYSTEM_INFORMATION_KEY).get(self.CLUSTER_ID_KEY),
                                                                   '')

            # Decrypt RabbitMQ Password
            decryption_key = encryptor.gen_key(cluster_id, ServiceTypes.RABBITMQ.value)
            self._password = encryptor.decrypt(decryption_key, self._password.encode('ascii'), "EgressProcessor")

            if self._iem_route_addr != "":
                logger.info("         Routing IEMs to host: %s" % self._iem_route_addr)
                logger.info("         Using IEM exchange: %s" % self._iem_route_exchange_name)
        except Exception as ex:
            logger.error(f"{self.MODULE_NAME}, _read_config: %r" % ex)

    def _get_default_amqp_config(self):
        return {
                    "virtual_host": self._virtual_host,
                    "exchange": self._exchange_name,
                    "username": self._username,
                    "password": self._password,
                    "hosts": self._hosts,
                    "exchange_queue": self._queue_name,
                    "exchange_type": "topic",
                    "routing_key": self._routing_key,
                    "durable": True,
                    "exclusive": False,
                    "retry_count": 1,
                    "port": 5672
                }

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
                self._ack_comm.send(message=self._jsonMsg)

            # Routing requests for IEM msgs sent from the LoggingMsgHandler
            elif self._jsonMsg.get("message").get("IEM_routing") is not None:
                log_msg = self._jsonMsg.get("message").get("IEM_routing").get("log_msg")
                self._log_debug("Routing IEM: %s" % log_msg)
                if self._iem_route_addr != "":
                    self._iem_comm.send(message=str(log_msg))
                else:
                    logger.warn(f"{self.MODULE_NAME}, Attempted to route IEM without a valid 'iem_route_addr' set.")
            else:
                self._add_signature()
                try:
                    self._default_comm.send(message=self._jsonMsg)
                except AmqpConnectionError:
                    logger.error(f"{self.MODULE_NAME}, _transmit_msg_on_exchange, amqp connectivity lost, adding message to consul {self._jsonMsg}")
                    store_queue.put(json.dumps(self._jsonMsg))

            # No exceptions thrown so success
            self._log_debug("_transmit_msg_on_exchange, Successfully Sent: %s" % self._jsonMsg)
            # If event is added by sensors, set it
            if self._event:
                self._event.set()

        except Exception as ex:
            logger.error(f"{self.MODULE_NAME}, _transmit_msg_on_exchange: %r" % ex)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(EgressProcessor, self).shutdown()
