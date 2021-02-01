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
                    over network
 ****************************************************************************
"""

import json
import pika
import os
import time

from cortx.sspl.framework.base.module_thread import ScheduledModuleThread
from cortx.sspl.framework.base.internal_msgQ import InternalMsgQ
from cortx.sspl.framework.utils.service_logging import logger
from cortx.sspl.framework.rabbitmq.rabbitmq_connector import RabbitMQSafeConnection
from cortx.sspl.json_msgs.messages.actuators.thread_controller import ThreadControllerMsg
from cortx.sspl.json_msgs.messages.actuators.ack_response import AckResponseMsg

import ctypes
try:
    use_security_lib=True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info("PlaneCntrlRMQegressProcessor, libsspl_sec not found, disabling authentication on egress msgs")
    use_security_lib=False


class PlaneCntrlRMQegressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles outgoing messages via rabbitMQ over network"""

    MODULE_NAME = "PlaneCntrlRMQegressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
    RABBITMQPROCESSOR       = MODULE_NAME.upper()
    EXCHANGE_NAME           = 'exchange_name'
    QUEUE_NAME              = 'queue_name'
    ROUTING_KEY             = 'routing_key'
    VIRT_HOST               = 'virtual_host'
    USER_NAME               = 'username'
    PASSWORD                = 'password'
    PRIMARY_RABBITMQ        = 'primary_rabbitmq_server'
    SECONDARY_RABBITMQ      = 'secondary_rabbitmq_server'
    SIGNATURE_USERNAME      = 'message_signature_username'
    SIGNATURE_TOKEN         = 'message_signature_token'
    SIGNATURE_EXPIRES       = 'message_signature_expires'


    @staticmethod
    def name():
        """ @return: name of the module."""
        return PlaneCntrlRMQegressProcessor.MODULE_NAME

    def __init__(self):
        super(PlaneCntrlRMQegressProcessor, self).__init__(self.MODULE_NAME,
                                                      self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(PlaneCntrlRMQegressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(PlaneCntrlRMQegressProcessor, self).initialize_msgQ(msgQlist)

        # Flag denoting that a shutdown message has been placed
        #  into our message queue from the main sspl_ll_d handler
        self._request_shutdown = False

        self._msg_sent_succesfull = True

        # Configure RabbitMQ Exchange to transmit messages
        self._connection = None
        self._read_config()

        # UUID and command of the current task being worked
        self._working_uuid = "N/A"
        self._working_command = "N/A"

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
            # Block on message queue until it contains an entry
            if self._msg_sent_succesfull:
                # Only get a new msg if we've successfully processed the current one
                self._jsonMsg, self._event = self._read_my_msgQ()

            if self._jsonMsg is not None:
                self._transmit_msg_on_exchange()

            # Loop thru all messages in queue until and transmit
            while not self._is_my_msgQ_empty():
                # Only get a new msg if we've successfully processed the current one
                if self._msg_sent_succesfull:
                    self._jsonMsg, self._event = self._read_my_msgQ()

                if self._jsonMsg is not None:
                    self._transmit_msg_on_exchange()

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.exception("PlaneCntrlRMQegressProcessor restarting")

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
            self._queue_name    = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.QUEUE_NAME,
                                                                 'ras_status')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.EXCHANGE_NAME,
                                                                 'ras_sspl')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ROUTING_KEY,
                                                                 'sspl_ll')
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
            self._primary_rabbitMQ_server   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PRIMARY_RABBITMQ,
                                                                 'localhost')
            self._secondary_rabbitMQ_server = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SECONDARY_RABBITMQ,
                                                                 'localhost')
            self._current_rabbitMQ_server = self._primary_rabbitMQ_server
            self._connection = RabbitMQSafeConnection(
                self._username, self._password, self._virtual_host,
                self._exchange_name, self._routing_key, self._queue_name
            )

        except Exception as ex:
            logger.exception("PlaneCntrlRMQegressProcessor, _read_config: %r" % ex)

    def _add_signature(self):
        """Adds the authentication signature to the message"""
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
        try:
            if self._jsonMsg.get("actuator_request_type") is not None and \
               self._jsonMsg.get("actuator_request_type").get("plane_controller") is not None:
                self._working_command  = self._jsonMsg.get("actuator_request_type").get("plane_controller").get("command")
                self._working_uuid = self._jsonMsg.get("sspl_ll_msg_header").get("uuid")
                logger.info("PlaneCntrlMsgHandler is currently working job task command: %s, uuid: %s" % \
                             (str(self._working_command ), str(self._working_uuid)))
                return

            # Check for a ack msg being sent and remove the currently working job uuid if job is completed
            elif self._jsonMsg.get("message") is not None and \
                 self._jsonMsg.get("message").get("actuator_response_type") is not None and \
                 self._jsonMsg.get("message").get("actuator_response_type").get("ack") is not None:

                uuid = self._jsonMsg.get("message").get("sspl_ll_msg_header").get("uuid")
                ack_msg = self._jsonMsg.get("message").get("actuator_response_type").get("ack").get("ack_msg")
                try:
                    ack_type = json.loads(self._jsonMsg.get("message").get("actuator_response_type").get("ack").get("ack_type"))
                except Exception as exi:
                    logger.info("PlaneCntrlRMQegressProcessor, _transmit_msg_on_exchange no ack_type: %s" % str(self._jsonMsg))
                    return

                # If it's a job status request then parse out the uuid from args that we're looking for
                if ack_type.get("command") is not None and \
                   ack_type.get("command") == "job_status" and \
                   ack_type.get("arguments") is not None:
                    uuid = ack_type.get("arguments")

                self._log_debug("Processing ack msg: %s, ack type: %s, uuid: %s" % (ack_msg, ack_type, uuid))

                # Check if the passing Ack msg has the same uuid as the one that was being worked on
                if self._working_uuid == uuid:
                    # If the ack msg is Not Found then change it to In work
                    if ack_msg == "Not Found":
                        self._jsonMsg["message"]["actuator_response_type"]["ack"]["ack_msg"] = "In Work"
                        logger.info("PlaneCntrlMsgHandler is working on job task command: %s, uuid: %s, ack_msg: %s" % \
                                    (str(self._working_command), str(uuid), "In Work"))
                    else:
                        # Task is no longer being worked on
                        if ack_msg is None or \
                           len(ack_msg) == 0:
                            ack_msg = "Completed"
                            self._jsonMsg["message"]["actuator_response_type"]["ack"]["ack_msg"] = ack_msg

                        logger.info("PlaneCntrlMsgHandler has completed job task command: %s, uuid: %s, ack_msg: %s" % \
                             (str(self._working_command), str(uuid), str(ack_msg)))
                        self._working_uuid = "N/A"

            msg_props = pika.BasicProperties()
            msg_props.content_type = "text/plain"

            self._add_signature()
            self._jsonMsg = json.dumps(self._jsonMsg).encode('utf8')
            self._connection.publish(exchange, routing_key, properties, body)
            # No exceptions thrown so success
            self._log_debug("_transmit_msg_on_exchange, Successfully Sent: %s" % self._jsonMsg)
            # If event is added by sensors, set it
            if self._event:
                self._event.set()
            self._msg_sent_succesfull = True
        except Exception as ex:
            logger.exception("PlaneCntrlRMQegressProcessor, _transmit_msg_on_exchange: %r" % ex)
            self._msg_sent_succesfull = False

    def _toggle_rabbitMQ_servers(self):
        """Toggle between hosts when a connection fails"""
        if self._current_rabbitMQ_server == self._primary_rabbitMQ_server:
            self._current_rabbitMQ_server = self._secondary_rabbitMQ_server
        else:
            self._current_rabbitMQ_server = self._primary_rabbitMQ_server

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(PlaneCntrlRMQegressProcessor, self).shutdown()
