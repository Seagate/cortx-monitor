"""
 ****************************************************************************
 Filename:          logging_processor.py
 Description:       Handles logging Messages to journald coming directly
                    from the messaging bus exchange sspl_iem
 Creation Date:     02/18/2015
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
import time
from syslog import (LOG_ALERT, LOG_CRIT, LOG_DEBUG, LOG_EMERG, LOG_ERR,
                    LOG_INFO, LOG_NOTICE, LOG_WARNING)

import pika
from eos.utils.amqp import AmqpConnectionError

from framework.messaging.utils import get_messaging_config
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.utils.messaging_factory import messaging_factory
from framework.utils.autoemail import AutoEmail
from framework.utils.service_logging import logger
# Modules that receive messages from this module
from message_handlers.logging_msg_handler import LoggingMsgHandler

try:
   from systemd import journal
   use_journal=True
except ImportError:
    use_journal=False

LOGLEVELS = {
    "LOG_EMERG"   : LOG_EMERG,
    "LOG_ALERT"   : LOG_ALERT,
    "LOG_CRIT"    : LOG_CRIT,
    "LOG_ERR"     : LOG_ERR,
    "LOG_WARNING" : LOG_WARNING,
    "LOG_NOTICE"  : LOG_NOTICE,
    "LOG_INFO"    : LOG_INFO,
    "LOG_DEBUG"   : LOG_DEBUG
}

class LoggingProcessor(ScheduledModuleThread, InternalMsgQ):

    MODULE_NAME = "LoggingProcessor"
    PRIORITY    = 2

    # Section and keys in configuration file
    LOGGINGPROCESSOR    = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'
    QUEUE_NAME          = 'queue_name'
    ROUTING_KEY         = 'routing_key'
    VIRT_HOST           = 'virtual_host'

    @staticmethod
    def name():
        """ @return: name of the monitoring module."""
        return LoggingProcessor.MODULE_NAME

    def __init__(self):
        super(LoggingProcessor, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(LoggingProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(LoggingProcessor, self).initialize_msgQ(msgQlist)

        self._autoemailer = AutoEmail(conf_reader)

        # Get common messaging config
        messaging_config = get_messaging_config(section=self.LOGGINGPROCESSOR, 
                    keys=[(self.VIRT_HOST, "SSPL"), (self.EXCHANGE_NAME, "sspl-in"), 
                    (self.QUEUE_NAME, "iem-queue"), (self.ROUTING_KEY, "iem-key")])
        self._comm = messaging_factory.get_messaging_consumer(**messaging_config)
        try:
            self._comm.init()
        except AmqpConnectionError:
            logger.error(f"{self.MODULE_NAME} messaging connection is not initialized")

    def run(self):
        """Run the module periodically on its own thread."""
        #self._set_debug(True)
        #self._set_debug_persist(True)

        self._log_debug("Start accepting requests")
        try:
            self._comm.recv(callback_fn=self._process_msg)
        except Exception as ae:
            if self.is_running() is True:
                logger.info(f"{self.MODULE_NAME} ungracefully breaking out of run loop, restarting: {ae}")
                self._scheduler.enter(10, self._priority, self.run, ())
            else:
                logger.info(f"{self.MODULE_NAME} gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, body):
        """Parses the incoming message and hands off to the appropriate module"""
        try:
            # Encode and remove blankspace,\n,\t - Leaving as it might be useful
            #ingressMsgTxt = json.dumps(body, ensure_ascii=True).encode('utf8')
            #ingressMsg = json.loads(' '.join(ingressMsgTxt.split()))

            # Enable debugging if it's found in the message
            if "debug" in body.lower():
                self._set_debug(True)

            # Try encoding message to handle escape chars if present
            try:
                log_msg = body.encode('utf8')
            except Exception as de:
                self._log_debug("_process_msg, no encoding applied, writing to syslog")
                log_msg = body

            # See if there is log level at the beginning
            log_level = log_msg[0: log_msg.index(" ")]
            if LOGLEVELS.get(log_level) is not None:
                priority = LOGLEVELS[log_level]
                log_msg = log_msg[log_msg.index(" "):]
            else:
                priority = LOG_INFO  # Default to info log level
                log_level = "LOG_INFO"

            # See if there is an id available
            event_code = None
            try:
                event_code_start = log_msg.index("IEC:") + 4
                event_code_stop  = log_msg.index(":", event_code_start)

                # Parse out the event code and remove any blank spaces
                event_code = log_msg[event_code_start : event_code_stop].strip()
                self._log_debug("log_msg, event_code: %s" % event_code)
            except Exception as e:
                # Log message has no IEC to use as message_id in journal, ignoring
                self._log_debug(f'Log message has no IEC to use as message_id in journal, ignoring: error: {e}')

            # Not an IEM so just dump it to the journal and don't worry about email and routing back to CMU
            if event_code is None:
                if use_journal:
                    journal.send(log_msg, MESSAGE_ID=event_code, PRIORITY=priority,
                                 SYSLOG_IDENTIFIER="sspl-ll")
                else:
                    logger.info(log_msg)
            else:
                # Send the IEM to the logging msg handler to be processed
                internal_json_msg = json.dumps(
                    {"actuator_request_type" : {
                        "logging": {
                            "log_level": log_level,
                            "log_type": "IEM",
                            "log_msg": log_msg
                            }
                        }
                     })
                # Send the event to logging msg handler to send IEM message to journald
                self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

            # Acknowledge message was received
            self._comm.acknowledge()
        except Exception as ex:
            logger.error("_process_msg: %r" % ex)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(LoggingProcessor, self).shutdown()
        try:
            self._comm.stop()
        except pika.exceptions.ConnectionClosed:
            logger.info(f"{self.MODULE_NAME}, shutdown, messaging ConnectionClosed")
