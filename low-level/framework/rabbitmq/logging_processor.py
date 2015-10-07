"""
 ****************************************************************************
 Filename:          logging_processor.py
 Description:       Handles logging Messages to Syslog coming directly
                    from the RabbitMQ exchange sspl_iem
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

import pika
import os

from systemd import journal

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.utils.autoemail import AutoEmail

from syslog import (LOG_EMERG, LOG_ALERT, LOG_CRIT, LOG_ERR,
                    LOG_WARNING, LOG_NOTICE, LOG_INFO, LOG_DEBUG)
LOGLEVELS = [("emerg"    , 0),
             ("emergency", 0),
             ("alert"    , 1),
             ("critical" , 2),
             ("crit"     , 2),
             ("error"    , 3),
             ("warning"  , 4),
             ("warn"     , 4),
             ("notice"   , 5),
             ("info"     , 6),
             ("debug"    , 7),
             (""         , 6) #Identify no log level as info
            ]

class LoggingProcessor(ScheduledModuleThread, InternalMsgQ):

    MODULE_NAME = "LoggingProcessor"
    PRIORITY    = 2

    # Section and keys in configuration file
    LOGGINGPROCESSOR    = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'
    ROUTING_KEY         = 'routing_key'
    VIRT_HOST           = 'virtual_host'
    USER_NAME           = 'username'
    PASSWORD            = 'password'


    @staticmethod
    def name():
        """ @return: name of the monitoring module."""
        return LoggingProcessor.MODULE_NAME

    def __init__(self):
        super(LoggingProcessor, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(LoggingProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(LoggingProcessor, self).initialize_msgQ(msgQlist)

        self._autoemailer = AutoEmail(conf_reader)

        # Configure RabbitMQ Exchange to receive messages
        self._configure_exchange()

    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Start accepting requests")
        try:
            result = self._channel.queue_declare(exclusive=True)
            self._channel.queue_bind(exchange=self._exchange_name,
                                queue=result.method.queue,
                                routing_key=self._routing_key)

            self._channel.basic_consume(self._process_msg,
                                  queue=result.method.queue)

            self._channel.start_consuming()

        except Exception:
            if self.is_running() == True:
                logger.info("LoggingProcessor ungracefully breaking out of run loop, restarting.")
                logger.exception()
                self._scheduler.enter(10, self._priority, self.run, ())
            else:
                logger.info("LoggingProcessor gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, ch, method, properties, body):
        """Parses the incoming message and hands off to the appropriate module"""
        try:
            # Encode and remove whitespace,\n,\t - Leaving as it might be useful
            #ingressMsgTxt = json.dumps(body, ensure_ascii=True).encode('utf8')
            #ingressMsg = json.loads(' '.join(ingressMsgTxt.split()))

            # Enable debugging if it's found in the message
            if "debug" in body or "DEBUG" in body:
                self._set_debug(True)

            # Try encoding message to handle escape chars if present
            try:
                log_msg = body.encode('utf8')
            except Exception as de:
                self._log_debug("_process_msg, no encoding applied, writing to syslog")
                log_msg = body

            # See if there is an id available
            event_code = None
            try:
                event_code_start = log_msg.index("IEC:") + 4
                event_code_stop  = log_msg.index(":", event_code_start)

                # Parse out the event code and remove any white spaces
                event_code = log_msg[event_code_start : event_code_stop].strip()
                self._log_debug("log_msg, event_code: %s" % event_code)
            except:
                # Log message has no IEC to use as message_id in journal, ignoring
                pass

            # Write message to the journal
            for loglevel, priority in LOGLEVELS:
                # Parse the message for a log level and log the message
                if loglevel in log_msg or loglevel.upper() in log_msg:
                    # Send it to the journal with the appropriate arguments
                    journal.send(log_msg, MESSAGE_ID=event_code, PRIORITY=priority,
                                 SYSLOG_IDENTIFIER="sspl-ll")

                    # Send email if priority exceeds LOGEMAILER priority in /etc/sspl-ll.conf
                    result = self._autoemailer._send_email(log_msg, priority)
                    self._log_debug("Autoemailer result: %s" % result)

                    # Break to avoid resending log messages
                    break

            # Acknowledge message was received     
            ch.basic_ack(delivery_tag = method.delivery_tag)
        except Exception as ex:
            logger.exception("_process_msg: %r" % ex)

    def _configure_exchange(self):        
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.LOGGINGPROCESSOR,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')
            self._exchange_name = self._conf_reader._get_value_with_default(self.LOGGINGPROCESSOR,
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl_iem')
            self._routing_key   = self._conf_reader._get_value_with_default(self.LOGGINGPROCESSOR,
                                                                 self.ROUTING_KEY,
                                                                 'sspl_ll')           
            self._username      = self._conf_reader._get_value_with_default(self.LOGGINGPROCESSOR,
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password      = self._conf_reader._get_value_with_default(self.LOGGINGPROCESSOR,
                                                                 self.PASSWORD,
                                                                 'sspl4ever')

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
            logger.exception("_configure_exchange: %s" % ex)  


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(LoggingProcessor, self).shutdown()
        try:
            self._connection.close()
            self._channel.stop_consuming()
        except pika.exceptions.ConnectionClosed:
            logger.info("LoggingProcessor, shutdown, RabbitMQ ConnectionClosed")
        