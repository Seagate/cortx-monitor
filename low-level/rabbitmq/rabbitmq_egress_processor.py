"""
 ****************************************************************************
 Filename:          rabbitmq_egress_processor.py
 Description:       Handles outgoing messages via rabbitMQ
 Creation Date:     01/14/2015
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

from base.monitor_thread import ScheduledMonitorThread
from base.internal_msgQ import InternalMsgQ
from utils.service_logging import logger

class RabbitMQegressProcessor(ScheduledMonitorThread, InternalMsgQ):
    
    MODULE_NAME = "RabbitMQegressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
    RABBITMQPROCESSOR   = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'
    ROUTING_KEY         = 'routing_key'
    VIRT_HOST           = 'virtual_host'
    USER_NAME           = 'username'
    PASSWORD            = 'password'

    @staticmethod
    def name():
        """ @return name of the monitoring module."""
        return RabbitMQegressProcessor.MODULE_NAME
    
    def __init__(self):
        super(RabbitMQegressProcessor, self).__init__(self.MODULE_NAME,
                                                self.PRIORITY)            

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""               
        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RabbitMQegressProcessor, self).initialize(conf_reader)
        
        # Initialize internal message queues for this module
        super(RabbitMQegressProcessor, self).initializeMsgQ(msgQlist)
        
        # Configure RabbitMQ Exchange to transmit message
        self._configureExchange()
        
        # Display values used to configure pika from the config file
        logger.info ("RabbitMQegressProcessor, creds: %s,  %s" % (self._username, self._password))   
        logger.info ("RabbitMQegressProcessor, exchange: %s, routing_key: %s, vhost: %s" % 
                     (self._exchange_name, self._routing_key, self._virtual_host))                 
        
    def run(self):
        """Run the module periodically on its own thread. """
        logger.info("Starting thread for '%s'", self.name())
        
        try:
            # Block on message queue until it contains an entry 
            jsonMsg = self._readMyMsgQ()
            self._transmitMsgOnExchange(jsonMsg)    
 
            # Loop thru all messages in queue until and transmit        
            while not self._isMyMsgQempty():
                jsonMsg = self._readMyMsgQ()
                self._transmitMsgOnExchange(jsonMsg)
             
        except Exception as ex:
            # Log it and restart the whole process when a failure occurs      
            logger.exception("RabbitMQegressProcessor restarting")            
         
        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(0, self._priority, self.run, ())    
        logger.info("Finished thread for '%s'", self.name())
        
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
            logger.exception("RabbitMQegressProcessor, configureExchange: %s" % ex)
          
    def _transmitMsgOnExchange(self, jsonMsg):
        """Transmit json message onto RabbitMQ exchange"""
        logger.info("RabbitMQegressProcessor, transmitMsgOnExchange, jsonMsg: %s" % jsonMsg)
   
        try:           
            creds       = pika.PlainCredentials(self._username, self._password)
            connection  = pika.BlockingConnection(
                                    pika.ConnectionParameters(host='localhost', 
                                                              virtual_host=self._virtual_host,
                                                              credentials=creds))
            channel     = connection.channel()
            channel.exchange_declare(exchange=self._exchange_name, exchange_type='topic', 
                                     durable=True)
            
            msg_props = pika.BasicProperties()
            msg_props.content_type = "text/plain"
            
            # Publish json message
            channel.basic_publish(exchange=self._exchange_name, 
                                  routing_key=self._routing_key,
                                  properties=msg_props, 
                                  body=str(jsonMsg))             

            # No exceptions thrown so success
            logger.info ("_transmitMsgOnExchange, Successfully Sent: %s" % jsonMsg)
            connection.close()
            del(connection)
             
        except Exception as ex:
            logger.exception("RabbitMQegressProcessor, transmitMsgOnExchange: %s" % ex)
                  
        