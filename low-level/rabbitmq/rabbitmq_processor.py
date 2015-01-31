"""
 ****************************************************************************
 Filename:          rabbitmq_processor.py
 Description:       Handles asynchronous messaging via rabbitMQ
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

import Queue
import pika
import os

from base.monitor_thread import ScheduledMonitorThread 
from utils.service_logging import logger

class RabbitMQprocessor(ScheduledMonitorThread):
     
    MODULE_NAME = "RabbitMQprocessor"
    PRIORITY = 1

    # Section and keys in configuration file
    RABBITMQPROCESSOR   = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'
    ROUTING_KEY         = 'routing_key'
    VIRT_HOST           = 'virtual_host'
    USER_NAME           = 'username'
    PASSWORD            = 'password'

    @staticmethod
    def name():
        """ @return name of the monitoring module. """
        return RabbitMQprocessor.MODULE_NAME

    def __init__(self):
        super(RabbitMQprocessor, self).__init__(self.MODULE_NAME,
                                                self.PRIORITY)    

    def initialize(self, rabbitMsgQ, conf_reader):
        """initialize method contains conf_reader if needed"""
        super(RabbitMQprocessor, self).initialize(rabbitMsgQ,
                                                    conf_reader) 
        # Configure RabbitMQ Exchange to transmit message
        self._configureExchange()
        
    def run(self):
        """Run the monitoring periodically on its own thread. """
        super(RabbitMQprocessor, self).run()        
        logger.info("Starting thread for '%s'", self.name())    
        
        try:
            # Check message queue and transmit any messages over the rabbitMQ 
            if not self.isRabbitMsgQempty():            
                
                # Loop thru all messages in queue until it's empty and transmit        
                while not self.isRabbitMsgQempty():
                    jsonMsg = self._readRabbitMQ()
                    
                    # TODO: Validation checking of json message against the schemas
                    self._transmitMsgOnExchange(jsonMsg)       
                         
        except Exception as ex:
            # Log it and restart the whole process when a failure occurs      
            logger.exception("DriveManagerMonitor restarting")
            self._scheduler.enter(10, self._priority, self.run, ())  
        
        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(10, self._priority, self.run, ())    
        logger.info("Finished thread for '%s'", self.name())
        
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DriveManagerMonitor, self).shutdown()
        
    def _configureExchange(self):        
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR, 
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
            
            logger.info("RabbitMQprocessor, configureExchange, exchange_name: %s, " \
                         "routing_key: %s, username: %s, password: %s" % 
                         (self._exchange_name, self._routing_key, self._username, self._password))
            
        except Exception as ex:
            logger.exception("RabbitMQprocessor, configureExchange: %s" % ex)
          
    def _transmitMsgOnExchange(self, jsonMsg):
        """Transmit json message onto RabbitMQ exchange"""
        logger.info("RabbitMQprocessor, transmitMsgOnExchange, transmitting jsonMsg: %s" % jsonMsg)
   
        try:
            # Configure pika with credentials from the config file
            logger.info ("_transmitMsgOnExchange, creds: %s,  %s" % (self._username, self._password))   
            logger.info ("_transmitMsgOnExchange, exchange, routing_key: %s, %s" % (self._exchange_name, self._routing_key))
            logger.info ("_transmitMsgOnExchange, vhost, jsonMsg: %s, %s" % (self._virtual_host, jsonMsg))
            
            creds       = pika.PlainCredentials(self._username, self._password)
            connection  = pika.BlockingConnection(
                                    pika.ConnectionParameters(host='localhost', 
                                                              virtual_host=self._virtual_host,
                                                              credentials=creds))
            channel     = connection.channel()
            channel.exchange_declare(exchange=self._exchange_name, exchange_type='topic', durable=True)
            
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
            logger.exception("RabbitMQprocessor, transmitMsgOnExchange: %s" % ex)
                  
        