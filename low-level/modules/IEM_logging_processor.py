# -*- coding: utf-8 -*-
"""
 ****************************************************************************
 Filename:          IEM_logging_actuator.py
 Description:       Handles IEM logging actuator requests
 Creation Date:     02/18/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.

 ****************************************************************************
 All relevant license information (GPL, FreeBSD, etc)
 ****************************************************************************
"""

import syslog
import pika
import os

from base.monitor_thread import ScheduledMonitorThread
from base.internal_msgQ import InternalMsgQ
from utils.service_logging import logger

class IEMloggingProcessor(ScheduledMonitorThread, InternalMsgQ):
    
    MODULE_NAME = "IEMloggingProcessor"
    PRIORITY    = 2

    # Section and keys in configuration file
    IEMLOGGINGPROCESSOR = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'
    ROUTING_KEY         = 'routing_key'
    VIRT_HOST           = 'virtual_host'
    USER_NAME           = 'username'
    PASSWORD            = 'password'


    @staticmethod
    def name():
        """ @return name of the monitoring module."""
        return IEMloggingProcessor.MODULE_NAME
    
    def __init__(self):
        super(IEMloggingProcessor, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(IEMloggingProcessor, self).initialize(conf_reader)
        
        # Initialize internal message queues for this module
        super(IEMloggingProcessor, self).initializeMsgQ(msgQlist)
        
        # Configure RabbitMQ Exchange to receive messages
        self._configureExchange()
        
        # Display values used to configure pika from the config file
        logger.info ("IEMloggingProcessor, creds: %s,  %s" % (self._username, self._password))   
        logger.info ("IEMloggingProcessor, exchange: %s, routing_key: %s, vhost: %s" % 
                     (self._exchange_name, self._routing_key, self._virtual_host))       
        
    def run(self):
        """Run the module periodically on its own thread. """
        logger.info("Starting thread for '%s'", self.name())
                
        try:
            creds       = pika.PlainCredentials(self._username, self._password)
            connection  = pika.BlockingConnection(
                                    pika.ConnectionParameters(host='localhost', 
                                                              virtual_host=self._virtual_host,
                                                              credentials=creds))
            channel     = connection.channel()
            
            channel.exchange_declare(exchange=self._exchange_name, type='topic', 
                                     durable=True)
            
            result = channel.queue_declare(exclusive=True)
            channel.queue_bind(exchange=self._exchange_name,
                               queue=result.method.queue,
                               routing_key=self._routing_key)
            
            channel.basic_consume(self._processMsg,
                                  queue=result.method.queue,
                                  no_ack=True)
            channel.start_consuming()
            
        except Exception as ex:
            # Log it and restart the whole process when a failure occurs      
            logger.exception("IEMloggingProcessor restarting")    
        
        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(0, self._priority, self.run, ())
        logger.info("Finished thread for '%s'", self.name())            
            
        
    def _processMsg(self, ch, method, properties, body):
        """Parses the incoming message and hands off to the appropriate module"""        
        try:            
            # Try encoding message to handle escape chars if present
            try:
                logMsg = body.encode('utf8')
            except Exception as de:
                logger.info("IEMloggingProcessor, decoding failed, dumping to syslog")
                logMsg = body
                
            syslog.syslog(logMsg)
            logger.info("IEMloggingProcessor, _processMsg logMsg: %s" % logMsg)
            
        except Exception as ex:
            logger.info("IEMloggingProcessor, Exception: %s" % ex)    
        
        
    def _configureExchange(self):        
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.IEMLOGGINGPROCESSOR, 
                                                                 self.VIRT_HOST,
                                                                 'SSPL')
            self._exchange_name = self._conf_reader._get_value_with_default(self.IEMLOGGINGPROCESSOR, 
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl_ll_bcast')
            self._routing_key   = self._conf_reader._get_value_with_default(self.IEMLOGGINGPROCESSOR, 
                                                                 self.ROUTING_KEY,
                                                                 'sspl_ll')           
            self._username      = self._conf_reader._get_value_with_default(self.IEMLOGGINGPROCESSOR, 
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password      = self._conf_reader._get_value_with_default(self.IEMLOGGINGPROCESSOR, 
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
            channel = connection.channel()
            channel.queue_declare(
                queue='SSPL-LL',
                durable=True
                )
            channel.exchange_declare(
                exchange=self._exchange_name,
                exchange_type='topic',
                durable=True
                )
            channel.queue_bind(
                queue='SSPL-LL',
                exchange=self._exchange_name,
                routing_key=self._routing_key
                )

        except Exception as ex:
            logger.exception("IEMloggingProcessor, configureExchange: %s" % ex)  
        
        
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(IEMloggingProcessor, self).shutdown()
        
