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

import json
import pika
import time
import sys

from cortx.utils.message_bus import MessageProducer
from cortx.utils.message_bus import MessageBus
from cortx.utils.message_bus.error import MessageBusError
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from .rabbitmq_connector import RabbitMQSafeConnection, connection_exceptions
from framework.utils import encryptor
from framework.utils.store_factory import store
from framework.utils import mon_utils
from framework.utils.store_queue import store_queue
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS

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
    RABBITMQPROCESSOR       = MODULE_NAME.upper()
    SIGNATURE_USERNAME      = 'message_signature_username'
    SIGNATURE_TOKEN         = 'message_signature_token'
    SIGNATURE_EXPIRES       = 'message_signature_expires'
    IEM_ROUTE_ADDR          = 'iem_route_addr'
    PRODUCER_ID             = 'producer_id'
    MESSAGE_TYPE            = 'message_type'
    METHOD                  = 'method'

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

        self._read_config()
        message_bus = MessageBus()
        self._producer = MessageProducer(message_bus, producer_id=self._producer_id, 
                                    message_type=self._message_type, method=self._method)


    def run(self):
        """Run the module periodically on its own thread. """
        self._log_debug("Start accepting requests")

        #self._set_debug(True)
        #self._set_debug_persist(True)

        try:
            # Loop thru all messages in queue until and transmit
            while not self._is_my_msgQ_empty():
                self._jsonMsg, self._event = self._read_my_msgQ()

                if self._jsonMsg is not None:
                    self._transmit_msg_on_exchange()

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.error("RabbitMQegressProcessor restarting")

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
            self._signature_user = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_USERNAME,
                                                                 'sspl-ll')
            self._signature_token = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_TOKEN,
                                                                 'FAKETOKEN1234')
            self._signature_expires = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_EXPIRES,
                                                                 "3600")
            self._producer_id = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                    self.PRODUCER_ID,
                                                                    "sspl_sensor")
            self._message_type = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                    self.MESSAGE_TYPE,
                                                                    "Alert")
            self._method = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                    self.METHOD,
                                                                    "Sync")

        except Exception as ex:
            logger.error("RabbitMQegressProcessor, _read_config: %r" % ex)

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

            self._jsonMsg["signature"] = str(sig.raw, encoding='utf-8')
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
                self._producer.send([json.dumps(self._jsonMsg)])

            # Routing requests for IEM msgs sent from the LoggingMsgHandler
            elif self._jsonMsg.get("message").get("IEM_routing") is not None:
                log_msg = self._jsonMsg.get("message").get("IEM_routing").get("log_msg")
                self._log_debug("Routing IEM: %s" % log_msg)
                if self._iem_route_addr != "":
                    self._producer.send([json.dumps(self._jsonMsg)])
                else:
                    logger.warn("RabbitMQegressProcessor, Attempted to route IEM without a valid 'iem_route_addr' set.")
            else:
                self._add_signature()
                try:
                    jsonMsg = json.dumps(self._jsonMsg)
                    self._producer.send([jsonMsg])
                except MessageBusError as e:
                    logger.error(f"RabbitMQegressProcessor, _transmit_msg_on_exchange, error {e} in producing message,\
                                    adding message to consul {self._jsonMsg}")
                    store_queue.put(jsonMsg)
                except Exception as err:
                    logger.error(f'RabbitMQegressProcessor, _transmit_msg_on_exchange, Unknown error {err} while publishing the message, adding to persistent store {self._jsonMsg}')
                    store_queue.put(jsonMsg)


            # No exceptions thrown so success
            self._log_debug("_transmit_msg_on_exchange, Successfully Sent: %s" % self._jsonMsg)
            # If event is added by sensors, set it
            if self._event:
                self._event.set()

        except Exception as ex:
            logger.error(f'RabbitMQegressProcessor, _transmit_msg_on_exchange, problem while publishing the message:{ex}, adding message to consul: {self._jsonMsg}')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQegressProcessor, self).shutdown()
