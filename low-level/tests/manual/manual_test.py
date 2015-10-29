#!/usr/bin/env python
"""
# ****************************************************************************
# Filename: manual_test.py
#
# Description: Class to easily run manual tests and start a consumer with a config file
#
# Creation Date: 06/22/2015
#
# Author: Alex Cordero <alexander.cordero@seagate.com>
#         Andy Kim <jihoon.kim@seagate.com>
#
# Do NOT modify or remove this copyright and confidentiality notice!
#
# Copyright (c) 2001 - 2015 Seagate Technology, LLC.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
# Portions are also trade secret. Any use, duplication, derivation, distribution
# or disclosure of this code, for any reason, not expressly authorized is
# prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
# ****************************************************************************
"""
import json
import pika
import socket
import sys
import ctypes
import os
from datetime import datetime

sys.path.insert(0, '../..')
from framework.utils.config_reader import ConfigReader
SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')

class ManualTest():
    # Section and keys in configuration file
    VIRTUALHOST         = "virtual_host"
    EXCHANGENAME        = "exchange_name"
    ACKEXCHANGENAME     = "ack_exchange_name"
    ROUTINGKEY          = "routing_key"
    USERNAME            = "username"
    PASSWORD            = "password"
    SIGNATURE_USERNAME  = 'message_signature_username'
    SIGNATURE_TOKEN     = 'message_signature_token'
    SIGNATURE_EXPIRES   = 'message_signature_expires'

    def __init__(self, module):
        '''
        @param module: the module to load in /etc/sspl_ll/conf
        @type string
        '''
        self.module_name   = module.upper()
        self.confReader()

    def confReader(self):
        path_to_conf_file = "/etc/sspl_ll.conf"

        try:
            conf_reader = ConfigReader(path_to_conf_file)

        except (IOError, ConfigReader.Error) as err:
            # We don't have logger yet, need to find log_level from conf file first
            print "[ Error ] when validating the configuration file %s :" % \
                path_to_conf_file
            print err
            print "Exiting ..."
            exit(os.EX_USAGE)

        self._virtualhost = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.VIRTUALHOST,
                                                    'SSPL')
        self._exchangename = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.EXCHANGENAME,
                                                    'sspl_halon')
        self._ackexchangename = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.ACKEXCHANGENAME,
                                                    'sspl_command_ack')
        self._routingkey = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.ROUTINGKEY,
                                                    'sspl_ll')
        self._username = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.USERNAME,
                                                    'sspluser')
        self._password = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.PASSWORD,
                                                    'sspl4ever')
        self._signature_user = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.SIGNATURE_USERNAME,
                                                    'sspl-ll')
        self._signature_token = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.SIGNATURE_TOKEN,
                                                    'ALOIUD986798df69a8koDISLKJ282983')
        self._signature_expires = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.SIGNATURE_EXPIRES,
                                                    "3600")


    def basicPublish(self, jsonfile = None, message = None):
        """Publishes message out to the rabbitmq server

        @param jsonfile = the file containing a json message to be sent to the server
        @type jsonfile = string
        @param message = A json message to be sent to the server
        @type message = string
        """
        creds = pika.PlainCredentials(self._username, self._password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', virtual_host=self._virtualhost, credentials=creds))
        channel = connection.channel()

        channel.exchange_declare(exchange=self._exchangename,
                         type='topic', durable=False)

        msg_props = pika.BasicProperties()
        msg_props.content_type = "text/plain"
        if jsonfile is not None:
            msg = open(jsonfile).read()

            #Convert msg to json format and add username, time til expire (seconds), current time, and security signature
            jsonMsg = json.loads(msg)
            jsonMsg["username"] = self._signature_user
            jsonMsg["expires"]  = int(self._signature_expires)
            jsonMsg["time"]     = str(datetime.now())

            authn_token_len = len(self._signature_token) + 1
            session_length  = int(self._signature_expires)
            token = ctypes.create_string_buffer(SSPL_SEC.sspl_get_token_length())

            SSPL_SEC.sspl_generate_session_token(
                                self._signature_user, authn_token_len,
                                self._signature_token, session_length, token)
            # Generate the signature
            msg_len = len(str(jsonMsg)) + 1
            sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
            #Calculates the security signature and stores it in sig
            SSPL_SEC.sspl_sign_message(msg_len, str(jsonMsg), self._signature_user,
                                   token, sig)
            #Add the signature calculated using the SSPL_SEC security libs
            jsonMsg["signature"] = str(sig.raw)

            #Convert the message back to plain text and send to consumer
            channel.basic_publish(exchange=self._exchangename,
                                  routing_key=self._routingkey,
                                  properties=msg_props,
                                  body=str(json.dumps(jsonMsg, ensure_ascii=True).encode('utf8')))
            print "Successfully Sent: %s" % jsonMsg

        elif message is not None:
            #Convert the message back to plain text and send to consumer
            channel.basic_publish(exchange=self._exchangename,
                                  routing_key=self._routingkey,
                                  properties=msg_props,
                                  body=str(message))
            print "Successfully Sent: %s" % message

        connection.close()
        del(connection)

    def basicConsume(self):
        """Starts consuming all messages sent
        This function should be run on a daemon thread because it will never exit willingly
        Sets the thread event object to true and copies all ingress messages to self.interthread_msg
        """

        creds = pika.PlainCredentials(self._username, self._password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', virtual_host=self._virtualhost, credentials=creds))
        channel = connection.channel()
        channel.exchange_declare(exchange=self._exchangename,
                         type='topic', durable=False)
        result = channel.queue_declare(exclusive=True)
        channel.queue_bind(exchange=self._exchangename,
                           queue=result.method.queue,
                   routing_key=self._routingkey)
        print ' [*] Waiting for json messages. To exit press CTRL+C'

        def callback(ch, method, properties, body):
            '''Called whenever a message is passed to the Consumer
            Verifies the authenticity of the signature with the SSPL_SEC libs
            Stores the message and alerts any waiting threads when an ingress message is processed
            '''
            ingressMsg = json.loads(body)
            username   = ingressMsg.get("username")
            signature  = ingressMsg.get("signature")
            message    = ingressMsg.get("message")
            msg_len    = len(message) + 1
            try:
                #Verifies the authenticity of an ingress message
                assert(SSPL_SEC.sspl_verify_message(msg_len, str(message), username, signature) == 0)
                #Sorts out any outgoing messages only processes *_response_type
                if ingressMsg.get("message").get("sensor_response_type") is not None or \
                    ingressMsg.get("message").get("actuator_response_type") is not None:
                    print " [x] %r" % (body,)
            except:
                print "Authentication failed on message: %s" % ingressMsg

            ch.basic_ack(delivery_tag = method.delivery_tag)

        #Sets the callback function to be used when start_consuming is called and specifies the queue to pull messages off of.
        channel.basic_consume(callback,
                              queue=result.method.queue)
        try:
          channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            
    def basicConsumeAck(self):
        """Starts consuming all messages sent on the ack channel
        This function should be run on a daemon thread because it will never exit willingly
        Sets the thread event object to true and copies all ingress messages to self.interthread_msg
        """

        creds = pika.PlainCredentials(self._username, self._password)
        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost', virtual_host=self._virtualhost, credentials=creds))
        channel = connection.channel()
        channel.exchange_declare(exchange=self._ackexchangename,
                         type='topic', durable=False)
        result = channel.queue_declare(exclusive=True)
        channel.queue_bind(exchange=self._ackexchangename,
                           queue=result.method.queue,
                   routing_key=self._routingkey)
        print ' [*] Waiting for json messages. To exit press CTRL+C'

        def callback(ch, method, properties, body):
            '''Called whenever a message is passed to the Consumer
            Verifies the authenticity of the signature with the SSPL_SEC libs
            Stores the message and alerts any waiting threads when an ingress message is processed
            '''
            ingressMsg = json.loads(body)
            username   = ingressMsg.get("username")
            signature  = ingressMsg.get("signature")
            message    = ingressMsg.get("message")
            msg_len    = len(message) + 1
            try:
                #Verifies the authenticity of an ingress message
                assert(SSPL_SEC.sspl_verify_message(msg_len, str(message), username, signature) == 0)
                #Sorts out any outgoing messages only processes *_response_type
                if ingressMsg.get("message").get("sensor_response_type") is not None or \
                    ingressMsg.get("message").get("actuator_response_type") is not None:
                    print " [x] %r" % (body,)
            except:
                print "Authentication failed on message: %s" % ingressMsg

            ch.basic_ack(delivery_tag = method.delivery_tag)

        #Sets the callback function to be used when start_consuming is called and specifies the queue to pull messages off of.
        channel.basic_consume(callback,
                              queue=result.method.queue)
        try:
          channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()

