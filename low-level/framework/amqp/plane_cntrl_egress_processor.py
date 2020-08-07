"""
 ****************************************************************************
 Filename:          plane_cntrl_egress_processor.py
 Description:       Handles outgoing messages via amqp over network
 Creation Date:     11/14/2016
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

from framework.amqp.utils import get_amqp_common_config
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.utils.amqp_factory import amqp_factory
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.ack_response import AckResponseMsg
from json_msgs.messages.actuators.thread_controller import ThreadControllerMsg

try:
    use_security_lib=True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info("PlaneCntrlEgressProcessor, libsspl_sec not found, disabling authentication on egress msgs")
    use_security_lib=False


class PlaneCntrlEgressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles outgoing messages via amqp over network"""

    MODULE_NAME = "PlaneCntrlEgressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
    AMQPPROCESSOR       = MODULE_NAME.upper()
    EXCHANGE_NAME           = 'exchange_name'
    QUEUE_NAME              = 'queue_name'
    ROUTING_KEY             = 'routing_key'
    VIRT_HOST               = 'virtual_host'
    
    PRIMARY_AMQP        = 'primary_amqp_server'
    SECONDARY_AMQP      = 'secondary_amqp_server'
    SIGNATURE_USERNAME      = 'message_signature_username'
    SIGNATURE_TOKEN         = 'message_signature_token'
    SIGNATURE_EXPIRES       = 'message_signature_expires'

    @staticmethod
    def name():
        """ @return: name of the module."""
        return PlaneCntrlEgressProcessor.MODULE_NAME

    def __init__(self):
        super(PlaneCntrlEgressProcessor, self).__init__(self.MODULE_NAME,
                                                      self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(PlaneCntrlEgressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(PlaneCntrlEgressProcessor, self).initialize_msgQ(msgQlist)

        # Flag denoting that a shutdown message has been placed
        #  into our message queue from the main sspl_ll_d handler
        self._request_shutdown = False

        self._msg_sent_succesfull = True

        self._read_config()

        # Get common amqp config
        amqp_config = self._get_amqp_config()
        self._comm = amqp_factory.get_amqp_producer(**amqp_config)
        self._comm.init()

        # UUID and command of the current task being worked
        self._working_uuid = "N/A"
        self._working_command = "N/A"

        # Display values used to configure pika from the config file
        self._log_debug("amqp user: %s" % self._username)
        self._log_debug("amqp exchange: %s, routing_key: %s, vhost: %s" %
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
            logger.exception(f"{self.MODULE_NAME} restarting")

        self._log_debug("Finished processing successfully")

        # Shutdown is requested by the sspl_ll_d shutdown handler
        #  placing a 'shutdown' msg into our queue which allows us to
        #  finish processing any other queued up messages.
        if self._request_shutdown is True:
            self.shutdown()
        else:
            self._scheduler.enter(1, self._priority, self.run, ())

    def _read_config(self):
        """Configure the amqp exchange with defaults available"""
        try:
            self._signature_user = self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                                 self.SIGNATURE_USERNAME,
                                                                 'sspl-ll')
            self._signature_token = self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                                 self.SIGNATURE_TOKEN,
                                                                 'FAKETOKEN1234')
            self._signature_expires = self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                                 self.SIGNATURE_EXPIRES,
                                                                 "3600")
            self._primary_amqp_server   = self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                                 self.PRIMARY_AMQP,
                                                                 'localhost')
            self._secondary_amqp_server = self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                                 self.SECONDARY_AMQP,
                                                                 'localhost')
            self._current_amqp_server = self._primary_amqp_server

        except Exception as ex:
            logger.exception(f"{self.MODULE_NAME}, _read_config: {ex}")

    def _get_amqp_config(self):
        amqp_config = {
            "virtual_host": self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                        self.VIRT_HOST, 'SSPL'),
            "exchange": self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                        self.EXCHANGE_NAME, 'ras_sspl'),
            "exchange_queue": self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                        self.QUEUE_NAME, 'ras_status'),
            "exchange_type": "topic",
            "routing_key": self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                        self.ROUTING_KEY, 'sspl_ll'),
            "durable": True,
            "exclusive": False,
            "retry_count": 5,
        }
        amqp_common_config = get_amqp_common_config()
        return { **amqp_config, **amqp_common_config }

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
        """Transmit json message onto amqp exchange"""
        try:
            if self._jsonMsg.get("actuator_request_type") is not None and \
               self._jsonMsg.get("actuator_request_type").get("plane_controller") is not None:
                self._working_command  = self._jsonMsg.get("actuator_request_type").get("plane_controller").get("command")
                self._working_uuid = self._jsonMsg.get("sspl_ll_msg_header").get("uuid")
                logger.info(f"{self.MODULE_NAME} is currently working job task command:{str(self._working_command)}, \
                     uuid: {str(self._working_uuid)}")
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
                    logger.info(f"{self.MODULE_NAME}, _transmit_msg_on_exchange no ack_type: {self._jsonMsg}")
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
                        logger.info(f"{self.MODULE_NAME} is working on job task command: %s, \
                            uuid: {str(self._working_command)}, ack_msg: {str(uuid)} In Work")
                    else:
                        # Task is no longer being worked on
                        if ack_msg is None or \
                           len(ack_msg) == 0:
                            ack_msg = "Completed"
                            self._jsonMsg["message"]["actuator_response_type"]["ack"]["ack_msg"] = ack_msg

                        logger.info(f"{self.MODULE_NAME} has completed job task command: \
                            {str(self._working_command)}, uuid: {str(uuid)}, ack_msg: {str(ack_msg)}")
                        self._working_uuid = "N/A"

            msg_props = pika.BasicProperties()
            msg_props.content_type = "text/plain"

            self._add_signature()
            self._comm.send(self._jsonMsg)
            # No exceptions thrown so success
            self._log_debug("_transmit_msg_on_exchange, Successfully Sent: %s" % self._jsonMsg)
            # If event is added by sensors, set it
            if self._event:
                self._event.set()
            self._msg_sent_succesfull = True
        except Exception as ex:
            logger.exception(f"{self.MODULE_NAME}, _transmit_msg_on_exchange: {ex}")
            self._msg_sent_succesfull = False

    def _toggle_amqp_servers(self):
        """Toggle between hosts when a connection fails"""
        if self._current_amqp_server == self._primary_amqp_server:
            self._current_amqp_server = self._secondary_amqp_server
        else:
            self._current_amqp_server = self._primary_amqp_server

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(PlaneCntrlEgressProcessor, self).shutdown()
