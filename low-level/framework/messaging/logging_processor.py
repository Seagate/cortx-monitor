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
  Description:       Handles logging Messages to journald coming directly
                    from the messaging bus exchange sspl_iem
 ****************************************************************************
"""

import json
from syslog import (LOG_ALERT, LOG_CRIT, LOG_DEBUG, LOG_EMERG, LOG_ERR,
                    LOG_INFO, LOG_NOTICE, LOG_WARNING)
import time

from cortx.utils.message_bus import MessageConsumer

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.utils.autoemail import AutoEmail
from framework.utils.conf_utils import CLUSTER, SRVNODE, SSPL_CONF, Conf
from framework.utils.service_logging import logger
# Modules that receive messages from this module
from message_handlers.logging_msg_handler import LoggingMsgHandler
from . import producer_initialized

try:
    from systemd import journal

    use_journal = True
except ImportError:
    use_journal = False

LOGLEVELS = {
    "LOG_EMERG": LOG_EMERG,
    "LOG_ALERT": LOG_ALERT,
    "LOG_CRIT": LOG_CRIT,
    "LOG_ERR": LOG_ERR,
    "LOG_WARNING": LOG_WARNING,
    "LOG_NOTICE": LOG_NOTICE,
    "LOG_INFO": LOG_INFO,
    "LOG_DEBUG": LOG_DEBUG
}


class LoggingProcessor(ScheduledModuleThread, InternalMsgQ):
    MODULE_NAME = "LoggingProcessor"
    PRIORITY = 2

    # Section and keys in configuration file
    PROCESSOR = MODULE_NAME.upper()
    EXCHANGE_NAME = 'exchange_name'
    QUEUE_NAME = 'queue_name'
    ROUTING_KEY = 'routing_key'
    VIRT_HOST = 'virtual_host'
    USER_NAME = 'username'
    PASSWORD = 'password'

    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
    CLUSTER_ID_KEY = 'cluster_id'
    NODE_ID_KEY = 'node_id'

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

        self._read_config()
        producer_initialized.wait()
        self._consumer = MessageConsumer(consumer_id=self._consumer_id,
                                         consumer_group=self._consumer_group,
                                         message_types=[self._message_type],
                                         auto_ack=False, offset=self._offset)

    def run(self):
        """Run the module periodically on its own thread."""
        # self._set_debug(True)
        # self._set_debug_persist(True)

        self._log_debug("Start accepting requests")
        try:
            while True:
                message = self._consumer.receive()
                if message:
                    logger.info(f"LoggingProcessor, Message Recieved: {message}")
                    self._process_msg(message)
                    self._consumer.ack()
                else:
                    time.sleep(1)
        except Exception as ae:
            if self.is_running() is True:
                logger.info(
                    "LoggingProcessor ungracefully breaking out of run loop, restarting: %s"
                    % ae)
                self._configure_exchange(retry=True)
                self._scheduler.enter(10, self._priority, self.run, ())
            else:
                logger.info(
                    "LoggingProcessor gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, body):
        """Parses the incoming message and hands off to the appropriate module"""
        try:
            # Encode and remove blankspace,\n,\t - Leaving as it might be useful
            # ingressMsgTxt = json.dumps(body, ensure_ascii=True).encode('utf8')
            # ingressMsg = json.loads(' '.join(ingressMsgTxt.split()))

            # Enable debugging if it's found in the message
            if "debug" in body.lower():
                self._set_debug(True)

            # Try encoding message to handle escape chars if present
            try:
                log_msg = body.encode('utf8')
            except Exception as de:
                logger.debug(
                    "_process_msg, no encoding applied, writing to syslog")
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
                event_code_stop = log_msg.index(":", event_code_start)

                # Parse out the event code and remove any blank spaces
                event_code = log_msg[event_code_start: event_code_stop].strip()
                self._log_debug("log_msg, event_code: %s" % event_code)
            except Exception as e:
                # Log message has no IEC to use as message_id in journal, ignoring
                self._log_debug(
                    'Log message has no IEC to use as message_id in journal, ignoring: error: {}'.format(
                        e))

            # Not an IEM so just dump it to the journal and don't worry about email and routing back to CMU
            if event_code is None:
                if use_journal:
                    journal.send(log_msg, MESSAGE_ID=event_code,
                                 PRIORITY=priority,
                                 SYSLOG_IDENTIFIER="sspl-ll")
                else:
                    logger.info(log_msg)
            else:
                # Send the IEM to the logging msg handler to be processed
                internal_json_msg = json.dumps(
                    {"actuator_request_type": {
                        "logging": {
                            "log_level": log_level,
                            "log_type": "IEM",
                            "log_msg": log_msg
                        }
                    }
                    })
                # Send the event to logging msg handler to send IEM message to journald
                self._write_internal_msgQ(LoggingMsgHandler.name(),
                                          internal_json_msg)

        except Exception as ex:
            logger.error("_process_msg: %r" % ex)

    def _read_config(self):
        """Configure with defaults available"""
        # Make methods locally available
        self._node_id = Conf.get(SSPL_CONF,
                                 f"{CLUSTER}>{SRVNODE}>{self.NODE_ID_KEY}",
                                 'SN01')
        self._consumer_id = Conf.get(SSPL_CONF,
                                     f"{self.PROCESSOR}>{self.CONSUMER_ID}",
                                     'sspl_in')
        self._consumer_group = Conf.get(SSPL_CONF,
                                        f"{self.PROCESSOR}>{self.CONSUMER_GROUP}",
                                        'cortx_monitor')
        self._message_type = Conf.get(SSPL_CONF,
                                      f"{self.PROCESSOR}>{self.MESSAGE_TYPE}",
                                      'IEM')
        self._offset = Conf.get(SSPL_CONF,
                                f"{self.PROCESSOR}>{self.OFFSET}",
                                'earliest')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(LoggingProcessor, self).shutdown()

