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

import syslog
import pika
import os

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

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
        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(LoggingProcessor, self).initialize(conf_reader)
        
        # Initialize internal message queues for this module
        super(LoggingProcessor, self).initializeMsgQ(msgQlist)
        
        # Configure RabbitMQ Exchange to receive messages
        self._configureExchange()
        
        # Display values used to configure pika from the config file 
        self._log_debug("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                       (self._exchange_name, self._routing_key, self._virtual_host))
        
    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Starting thread")
        try:
            result = self._channel.queue_declare(exclusive=True)
            self._channel.queue_bind(exchange=self._exchange_name,
                                queue=result.method.queue,
                                routing_key=self._routing_key)
            
            self._channel.basic_consume(self._processMsg,
                                  queue=result.method.queue)
            
            self._channel.start_consuming()

        except Exception:
            # Log it and restart the whole process when a failure occurs      
            logger.exception("LoggingProcessor restarting") 
            
            # Configure RabbitMQ Exchange to receive messages
            self._configureExchange()   
        
        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(0, self._priority, self.run, ())
        self._log_debug("Finished thread")
        
    def _processMsg(self, ch, method, properties, body):
        """Parses the incoming message and hands off to the appropriate module"""        
        try:            
            # Encode and remove whitespace,\n,\t - Leaving as it might be useful
            #ingressMsgTxt = json.dumps(body, ensure_ascii=True).encode('utf8')
            #ingressMsg = json.loads(' '.join(ingressMsgTxt.split()))

            # Try encoding message to handle escape chars if present
            try:
                logMsg = body.encode('utf8')
            except Exception as de:
                self._log_debug("_processMsg, no encoding applied, writing to syslog")
                logMsg = body
            
            # Write message to syslog
            syslog.syslog(logMsg)
            
            # Acknowledge message was received     
            ch.basic_ack(delivery_tag = method.delivery_tag)
        except Exception as ex:
            logger.exception("LoggingProcessor, _processMsg: %r" % ex)
        
    def _configureExchange(self):        
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.LOGGINGPROCESSOR,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')
            self._exchange_name = self._conf_reader._get_value_with_default(self.LOGGINGPROCESSOR,
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl_ll_bcast')
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
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    virtual_host=self._virtual_host,
                    credentials=creds
                    )
                )
            self._channel = connection.channel()
            self._channel.queue_declare(
                queue='SSPL-LL',
                durable=True
                )
            self._channel.exchange_declare(
                exchange=self._exchange_name,
                exchange_type='topic',
                durable=True
                )
            self._channel.queue_bind(
                queue='SSPL-LL',
                exchange=self._exchange_name,
                routing_key=self._routing_key
                )
            
        except Exception as ex:
            logger.exception("LoggingProcessor, configureExchange: %s" % ex)  
        
        
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(LoggingProcessor, self).shutdown()
        
