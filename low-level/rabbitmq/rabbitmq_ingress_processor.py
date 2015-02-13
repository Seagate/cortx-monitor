"""
 ****************************************************************************
 Filename:          rabbitmq_ingress_processor.py
 Description:       Handles incoming messages via rabbitMQ
 Creation Date:     02/11/2015
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

import pika
import os
from pika import exceptions
from pika.adapters import twisted_connection
from twisted.internet import defer, reactor, protocol, task

from base.monitor_thread import ScheduledMonitorThread
from base.internal_msgQ import InternalMsgQ
from utils.service_logging import logger

class RabbitMQingressProcessor(ScheduledMonitorThread, InternalMsgQ):
    
    MODULE_NAME = "RabbitMQingressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
    RABBITMQPROCESSOR   = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'
    QUEUE_NAME          = 'queue_name'
    ROUTING_KEY         = 'routing_key'
    VIRT_HOST           = 'virtual_host'
    USER_NAME           = 'username'
    PASSWORD            = 'password'

    @staticmethod
    def name():
        """ @return name of the monitoring module."""
        return RabbitMQingressProcessor.MODULE_NAME
    
    def __init__(self):
        super(RabbitMQingressProcessor, self).__init__(self.MODULE_NAME,
                                                self.PRIORITY)     

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""               
        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RabbitMQingressProcessor, self).initialize(conf_reader)
        
        # Initialize internal message queues for this module
        super(RabbitMQingressProcessor, self).initializeMsgQ(msgQlist)
        
        # Configure RabbitMQ Exchange to transmit message
        self._configureExchange()
        
        # Display values used to configure pika from the config file
        logger.info ("RabbitMQingressProcessor, creds: %s,  %s" % (self._username, self._password))   
        logger.info ("RabbitMQingressProcessor, exchange: %s, routing_key: %s, vhost: %s" % 
                     (self._exchange_name, self._routing_key, self._virtual_host))                 
        
    def run(self):
        """Run the module periodically on its own thread. """        
        logger.info("Starting thread for '%s'", self.name())
        
        try:
            parameters = pika.ConnectionParameters()
            
            cc = protocol.ClientCreator(reactor, twisted_connection.TwistedProtocolConnection, parameters)
            
            d = cc.connectTCP('localhost', 5672)
            
            d.addCallback(lambda protocol: protocol.ready)
            
            d.addCallback(self._consumeMsgs)

            logger.info("RabbitMQingressProcessor running reactor to process incoming messages")
            
            reactor.run()
        except Exception as ex:
            # Log it and restart the whole process when a failure occurs      
            logger.exception("RabbitMQingressProcessor restarting")    
        
        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(0, self._priority, self.run, ())
        logger.info("Finished thread for '%s'", self.name())
        
    @defer.inlineCallbacks
    def _consumeMsgs(self, connection):
        """Callback method blocks reading in messages from RabbitMQ"""
        logger.info("RabbitMQingressProcessor, consumeMsgs")
        
        channel = yield connection.channel()
        
        exchange = yield channel.exchange_declare(exchange=self._exchange_name, type='topic')
        
        queue = yield channel.queue_declare(queue=self._queue_name, auto_delete=False, exclusive=False)    
        
        yield channel.queue_bind(exchange=self._exchange_name, queue=self._queue_name, routing_key=self._routing_key)  
        
        yield channel.basic_qos(prefetch_count=1)    
        
        queue_object, consumer_tag = yield channel.basic_consume(queue=self._queue_name, no_ack=False)
    
        l = task.LoopingCall(_read, queue_object)
    
        l.start(0.01)
        
    @defer.inlineCallbacks
    def _read(self, queue_object):
        """Callback method handles messages read in from Twisted reactor"""
        ch,method,properties,body = yield queue_object.get()
        
        if body:
            logger.info("RabbitMQingressProcessor, read: %s" % body)
        else:
            logger.info("RabbitMQingressProcessor, body is null")
            
        logger.info("RabbitMQingressProcessor, read, ch: %s, method: %s, properties: %s" % 
                    (ch, method, properties))
        
        yield ch.basic_ack(delivery_tag=method.delivery_tag)

                
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DriveManagerMonitor, self).shutdown()
        
    def _configureExchange(self):        
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.VIRT_HOST,
                                                                 'SSPL')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl_ll_bcast')
            self._queue_name    = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.QUEUE_NAME,
                                                                 'SSPL-LL')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.ROUTING_KEY,
                                                                 'sspl_ll')           
            self._username      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
                                                                 self.PASSWORD,
                                                                 'sspl4ever')            
        except Exception as ex:
            logger.exception("RabbitMQingressProcessor, configureExchange: %s" % ex)
          
                  
        