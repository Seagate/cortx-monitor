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
"""

import pika
import json
import os

from jsonschema import Draft3Validator
from jsonschema import validate

from pika import exceptions

from base.module_thread import ScheduledModuleThread
from base.internal_msgQ import InternalMsgQ
from utils.service_logging import logger

# Import message handlers to hand off messages
from message_handlers.logging_msg_handler import LoggingMsgHandler


class RabbitMQingressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles incoming messages via rabbitMQ"""
    
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

    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Request.json"


    @staticmethod
    def name():
        """ @return: name of the module."""
        return RabbitMQingressProcessor.MODULE_NAME
    
    def __init__(self):
        super(RabbitMQingressProcessor, self).__init__(self.MODULE_NAME,
                                                       self.PRIORITY)     
        
        # Read in the monitor schema for validating messages
        dir = os.path.dirname(__file__)
        fileName = os.path.join(dir, '..', '..', 'json_msgs',
                                'schemas', 'actuators',
                                self.JSON_ACTUATOR_SCHEMA)
        
        with open(fileName, 'r') as f:
            _schema = f.read()
        
        # Remove tabs and newlines
        self._schema = json.loads(' '.join(_schema.split()))
        
        # Validate the schema
        Draft3Validator.check_schema(self._schema)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""               
        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RabbitMQingressProcessor, self).initialize(conf_reader)
        
        # Initialize internal message queues for this module
        super(RabbitMQingressProcessor, self).initializeMsgQ(msgQlist)
        
        # Configure RabbitMQ Exchange to receive messages
        self._configure_exchange()
        
        # Display values used to configure pika from the config file 
        self._log_debug("RabbitMQ user: %s" % self._username)
        self._log_debug("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                      (self._exchange_name, self._routing_key, self._virtual_host))

    def run(self):
        """Run the module periodically on its own thread. """        
        self._log_debug("Starting thread")
        
        try:            
            result = self._channel.queue_declare(exclusive=True)
            self._channel.queue_bind(exchange=self._exchange_name,
                               queue=result.method.queue,
                               routing_key=self._routing_key)

            self._channel.basic_consume(self._process_msg,
                                  queue=result.method.queue)                                 
            self._channel.start_consuming()
            
        except Exception:
            # Log it and restart the whole process when a failure occurs      
            logger.exception("RabbitMQingressProcessor restarting")  
            
            # Configure RabbitMQ Exchange to receive messages
            self._configureExchange()  
        
        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(0, self._priority, self.run, ())
        self._log_debug("Finished thread")
        
    def _process_msg(self, ch, method, properties, body):
        """Parses the incoming message and hands off to the appropriate module"""        
        ingressMsg = {}
        try:                                    
            ingressMsg = json.loads(body)            
                        
            # Get the message type
            msgType = ingressMsg.get("actuator_msg_type")            
            
            # We only handle incoming actuator requests, ignore anything else
            if msgType is None:
                return
            
            # Check for debugging being activated in the message header
            self._check_debug(ingressMsg)
            self._log_debug("_process_msg, ingressMsg: %s" % ingressMsg)

            # Validate against the actuator schema
            validate(ingressMsg, self._schema)
            
            self._log_debug("_process_msg, msgType: %s" % msgType)

            # Hand off to appropriate module based on message type
            if msgType.get("logging"):
                self._writeInternalMsgQ(LoggingMsgHandler.name(), ingressMsg)

            elif msgType.get("drive_manager"):
                self._writeInternalMsgQ(ActuatorMsgHandler.name(), ingressMsg)
            
            # ... handle other incoming messages that have been validated                                
            
            # Acknowledge message was received
            ch.basic_ack(delivery_tag = method.delivery_tag)
                          
        except Exception as ex:
            logger.exception("_process_msg unrecognized message: %r" % ingressMsg)                 
                         
        
    def _configure_exchange(self):        
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
            logger.exception("_configure_exchange: %r" % ex)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DriveManagerMonitor, self).shutdown()
        
         