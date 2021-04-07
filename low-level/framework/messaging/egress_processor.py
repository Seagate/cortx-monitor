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
import time

from cortx.utils.message_bus import MessageProducer
from cortx.utils.message_bus.error import MessageBusError

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.utils.conf_utils import SSPL_CONF, Conf
from framework.utils.service_logging import logger
from framework.utils.store_queue import StoreQueue
from . import producer_initialized

try:
    use_security_lib = True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info(
        "EgressProcessor, libsspl_sec not found, disabling authentication on egress msgs")
    use_security_lib = False


class EgressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles outgoing messages via messaging bus over localhost."""

    MODULE_NAME = "EgressProcessor"
    PRIORITY = 1

    # Section and keys in configuration file
    PROCESSOR = MODULE_NAME.upper()
    SIGNATURE_USERNAME = 'message_signature_username'
    SIGNATURE_TOKEN = 'message_signature_token'
    SIGNATURE_EXPIRES = 'message_signature_expires'
    IEM_ROUTE_ADDR = 'iem_route_addr'
    PRODUCER_ID = 'producer_id'
    MESSAGE_TYPE = 'message_type'
    METHOD = 'method'

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

        self.store_queue = StoreQueue()
        # Flag denoting that a shutdown message has been placed
        #  into our message queue from the main sspl_ll_d handler
        self._request_shutdown = False

        self._read_config()
        self._producer = MessageProducer(producer_id=self._producer_id,
                                         message_type=self._message_type,
                                         method=self._method)
        producer_initialized.set()

    def run(self):
        """Run the module periodically on its own thread. """
        self._log_debug("Start accepting requests")

        # self._set_debug(True)
        # self._set_debug_persist(True)

        try:
            # Loop thru all messages in queue until and transmit
            while not self._is_my_msgQ_empty():
                self._jsonMsg, self._event = self._read_my_msgQ()

                if self._jsonMsg is not None:
                    self._transmit_msg_on_exchange()

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.error("EgressProcessor restarting")

        self._log_debug("Finished processing successfully")

        # Shutdown is requested by the sspl_ll_d shutdown handler
        #  placing a 'shutdown' msg into our queue which allows us to
        #  finish processing any other queued up messages.
        if self._request_shutdown is True:
            self.shutdown()
        else:
            self._scheduler.enter(1, self._priority, self.run, ())

    def _read_config(self):
        """Read the messaging bus configs."""
        try:
            self._signature_user = Conf.get(SSPL_CONF,
                                            f"{self.PROCESSOR}>{self.SIGNATURE_USERNAME}",
                                            'sspl-ll')
            self._signature_token = Conf.get(SSPL_CONF,
                                             f"{self.PROCESSOR}>{self.SIGNATURE_TOKEN}",
                                             'FAKETOKEN1234')
            self._signature_expires = Conf.get(SSPL_CONF,
                                               f"{self.PROCESSOR}>{self.SIGNATURE_EXPIRES}",
                                               "3600")
            self._producer_id = Conf.get(SSPL_CONF,
                                         f"{self.PROCESSOR}>{self.PRODUCER_ID}",
                                         "sspl-sensor")
            self._message_type = Conf.get(SSPL_CONF,
                                          f"{self.PROCESSOR}>{self.MESSAGE_TYPE}",
                                          "alerts")
            self._method = Conf.get(SSPL_CONF,
                                    f"{self.PROCESSOR}>{self.METHOD}",
                                    "sync")

        except Exception as ex:
            logger.error("EgressProcessor, _read_config: %r" % ex)

    def _add_signature(self):
        """Adds the authentication signature to the message"""
        self._log_debug("_add_signature, jsonMsg: %s" % self._jsonMsg)
        self._jsonMsg["username"] = self._signature_user
        self._jsonMsg["expires"] = int(self._signature_expires)
        self._jsonMsg["time"] = str(int(time.time()))

        if use_security_lib:
            authn_token_len = len(self._signature_token) + 1
            session_length = int(self._signature_expires)
            token = ctypes.create_string_buffer(
                SSPL_SEC.sspl_get_token_length())

            SSPL_SEC.sspl_generate_session_token(
                self._signature_user, authn_token_len,
                self._signature_token, session_length, token)

            # Generate the signature
            msg_len = len(self._jsonMsg) + 1
            sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
            SSPL_SEC.sspl_sign_message(msg_len, str(self._jsonMsg),
                                       self._signature_user,
                                       token, sig)

            self._jsonMsg["signature"] = str(sig.raw, encoding='utf-8')
        else:
            self._jsonMsg["signature"] = "SecurityLibNotInstalled"

    def _transmit_msg_on_exchange(self):
        """Transmit json message onto messaging bus."""
        self._log_debug(
            "_transmit_msg_on_exchange, jsonMsg: %s" % self._jsonMsg)

        try:
            # Check for shut down message from sspl_ll_d and set a flag to shutdown
            #  once our message queue is empty
            if self._jsonMsg.get("message").get(
                    "actuator_response_type") is not None and \
                    self._jsonMsg.get("message").get(
                        "actuator_response_type").get(
                        "thread_controller") is not None and \
                    self._jsonMsg.get("message").get(
                        "actuator_response_type").get("thread_controller").get(
                        "thread_response") == \
                    "SSPL-LL is shutting down":
                logger.info(
                    "EgressProcessor, _transmit_msg_on_exchange, received"
                    "global shutdown message from sspl_ll_d")
                self._request_shutdown = True

            # Publish json message to the correct channel
            # NOTE: We need to route ThreadController messages to ACK channel.
            # We can't modify schema as it will affect other modules too. As a
            # temporary solution we have added a extra check to see if actuator_response_type
            # is "thread_controller".
            # TODO: Find a proper way to solve this issue. Avoid changing
            # core egress processor code
            if self._jsonMsg.get("message").get(
                    "actuator_response_type") is not None and \
                    (self._jsonMsg.get("message").get(
                        "actuator_response_type").get("ack") is not None or
                     self._jsonMsg.get("message").get(
                         "actuator_response_type").get(
                         "thread_controller") is not None):
                self._add_signature()
                self._producer.send([json.dumps(self._jsonMsg)])
                logger.debug(
                    "_transmit_msg_on_exchange, Successfully Sent: %s" % self._jsonMsg)

            # Routing requests for IEM msgs sent from the LoggingMsgHandler
            elif self._jsonMsg.get("message").get("IEM_routing") is not None:
                log_msg = self._jsonMsg.get("message").get("IEM_routing").get(
                    "log_msg")
                if self._iem_route_addr != "":
                    self._producer.send([json.dumps(self._jsonMsg)])
                else:
                    logger.warn(
                        "EgressProcessor, Attempted to route IEM without a valid 'iem_route_addr' set.")
                logger.debug(
                    "_transmit_msg_on_exchange, Successfully Sent: %s" % log_msg)
            else:
                self._add_signature()
                jsonMsg = json.dumps(self._jsonMsg)
                try:
                    if self.store_queue.is_empty():
                        self._producer.send([jsonMsg])
                        logger.info(f"Published Alert: {jsonMsg}")
                    else:
                        logger.info("'Accumulated msg queue' is not Empty." +
                                    " Adding the msg to the end of the queue")
                        self.store_queue.put(jsonMsg)
                except MessageBusError as e:
                    logger.error(
                        f"EgressProcessor, _transmit_msg_on_exchange, error {e} in producing message,\
                                    adding message to consul {self._jsonMsg}")
                    self.store_queue.put(jsonMsg)
                except Exception as err:
                    logger.error(
                        f'EgressProcessor, _transmit_msg_on_exchange, Unknown error {err} while publishing the message, adding to persistent store {self._jsonMsg}')
                    self.store_queue.put(jsonMsg)

            # If event is added by sensors, set it
            if self._event:
                self._event.set()

        except Exception as ex:
            logger.error(
                f'EgressProcessor, _transmit_msg_on_exchange, problem while publishing the message:{ex}, adding message to consul: {self._jsonMsg}')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(EgressProcessor, self).shutdown()
