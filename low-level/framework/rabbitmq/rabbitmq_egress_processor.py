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
"""

import pika
import os

from base.module_thread import ScheduledModuleThread
from base.internal_msgQ import InternalMsgQ
from utils.service_logging import logger

class RabbitMQegressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles outgoing messages via rabbitMQ"""
    
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
        """ @return: name of the module."""
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
        self._readConfig()
        self._getConnection()
        
        # Display values used to configure pika from the config file   
        self._log_debug ("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                       (self._exchange_name, self._routing_key, self._virtual_host))    
        
    def run(self):
        """Run the module periodically on its own thread. """
        self._log_debug("Starting thread")
        
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
            
            # Configure RabbitMQ Exchange to receive messages
            self._configureExchange()        
         
        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(0, self._priority, self.run, ())    
        self._log_debug("Finished thread")
        
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DriveManagerMonitor, self).shutdown()
        
    def _readConfig(self):        
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
            logger.exception("RabbitMQegressProcessor, _readConfig: %s" % ex)
    
    def _getConnection(self):     
        try:   
            # ensure the rabbitmq queues/etc exist
            creds = pika.PlainCredentials(self._username, self._password)
            self._connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host='localhost',
                    virtual_host=self._virtual_host,
                    credentials=creds
                    )
                )
            channel = self._connection.channel()
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
            return channel
        except Exception as ex:
            logger.exception("RabbitMQegressProcessor, _getConnection: %s" % ex)
          
    def _transmitMsgOnExchange(self, jsonMsg):
        """Transmit json message onto RabbitMQ exchange"""
        self._log_debug("_transmitMsgOnExchange, jsonMsg: %s" % jsonMsg)
   
        try:            
            msg_props = pika.BasicProperties()
            msg_props.content_type = "text/plain"
            
            channel = self._getConnection()
            
            # Publish json message
            channel.basic_publish(exchange=self._exchange_name, 
                                  routing_key=self._routing_key,
                                  properties=msg_props, 
                                  body=str(jsonMsg))

            # No exceptions thrown so success
            self._log_debug("_transmitMsgOnExchange, Successfully Sent: %s" % jsonMsg)
            self._connection.close()
            del(self._connection)
             
        except Exception as ex:
            logger.exception("RabbitMQegressProcessor, transmitMsgOnExchange: %s" % ex)
                  

