#!/usr/bin/env python
# encoding: utf-8
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
import socket
import sys
import ctypes
import os
import time
import uuid
import threading
from datetime import datetime

try:
    import pika
except ImportError:
    print("Error importing python-pika package")
    
try:
    from jsonschema import Draft3Validator
    from jsonschema import validate
except ImportError:
    print("Error importing python-jsonschema package")

sys.path.insert(0, '../..')
from framework.utils.service_logging import init_logging
from framework.utils.service_logging import logger
from framework.utils.config_reader import ConfigReader

try:
    use_security_lib=True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    use_security_lib=False

class ManualTest():
    # Section and keys in configuration file
    VIRTUALHOST         = "virtual_host"
    INGRESSQUEU         = "queue_name"
    QUEUE_NAME          = "queue_name"
    EXCHANGENAME        = "exchange_name"
    ACKEXCHANGENAME     = "ack_exchange_name"
    ROUTINGKEY          = "routing_key"
    USERNAME            = "username"
    PASSWORD            = "password"
    SIGNATURE_USERNAME  = 'message_signature_username'
    SIGNATURE_TOKEN     = 'message_signature_token'
    SIGNATURE_EXPIRES   = 'message_signature_expires'
    PRIMARY_RABBITMQ    = 'primary_rabbitmq_server'
    SECONDARY_RABBITMQ  = 'secondary_rabbitmq_server'

    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Request.json"
    JSON_SENSOR_SCHEMA   = "SSPL-LL_Sensor_Request.json"

    def __init__(self, module, start_threads=True):
        '''
        @param module: the module to load in /etc/sspl_ll/conf
        @type string
        '''
 
        # Initialize logging
        try:
            init_logging("sspl-ll-cli", "DEBUG")

        except Exception as err:
            # We don't have logger since it threw an exception, use generic 'print'
            print "[ Error ] when initializing logging :"
            print err
            print "Exiting ..."
            sys.exit(os.EX_USAGE)

        self.module_name = module.upper()
        self.confReader()

        # Read in the actuator schema for validating messages
        dir = os.path.dirname(__file__)
        schema_file = os.path.join(dir, '..', '..', 'json_msgs',
                                   'schemas', 'actuators',
                                   self.JSON_ACTUATOR_SCHEMA)
        self._actuator_schema = self._load_schema(schema_file)

        # Read in the sensor schema for validating messages
        schema_file = os.path.join(dir, '..', '..', 'json_msgs',
                                   'schemas', 'sensors',
                                   self.JSON_SENSOR_SCHEMA)
        self._sensor_schema = self._load_schema(schema_file)

        if start_threads:
            # Start up threads to receive responses
            self._basic_consumet = threading.Thread(target=self.basicConsume)
            self._basic_consumet.setDaemon(True)
            self._basic_consumet.start()

            if self.module_name == "RABBITMQEGRESSPROCESSOR":
                self._basic_consume_ackt = threading.Thread(target=self.basicConsumeAck)
                self._basic_consume_ackt.setDaemon(True)
                self._basic_consume_ackt.start()
                self._durable = False
            else:
                self._durable = True
        else:
            self._durable = False

        self._alldata = True
        self._indent = True
        self._request_uuid = None
        self._msg_received = False
        self._total_msg_received = 0
        self._total_ack_msg_received = 0
        self._print_data = ""

    def _load_schema(self, schema_file):
        """Loads a schema from a file and validates

        @param string schema_file     location of schema on the file system
        @return string                Trimmed and validated schema
        """
        with open(schema_file, 'r') as f:
            schema = f.read()

        # Remove tabs and newlines
        schema_trimmed = json.loads(' '.join(schema.split()))

        # Validate the actuator schema
        Draft3Validator.check_schema(schema_trimmed)

        return schema_trimmed

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

        if self.module_name == "RABBITMQEGRESSPROCESSOR":
            self._ingress_queue = conf_reader._get_value_with_default(
                                                        self.module_name,
                                                        self.QUEUE_NAME,
                                                        'SSPL-LL')
        elif self.module_name == "PLANECNTRLRMQEGRESSPROCESSOR":
            self._ingress_queue = conf_reader._get_value_with_default(
                                                        self.module_name,
                                                        self.QUEUE_NAME,
                                                        'ras_status')

        if self.module_name == "RABBITMQEGRESSPROCESSOR":
            self._egress_queue = conf_reader._get_value_with_default(
                                                        self.module_name,
                                                        self.QUEUE_NAME,
                                                        'SSPL-LL')
        elif self.module_name == "PLANECNTRLRMQEGRESSPROCESSOR":
            self._egress_queue = conf_reader._get_value_with_default(
                                                        self.module_name,
                                                        self.QUEUE_NAME,
                                                        'ras_control')

        self._exchangename = conf_reader._get_value_with_default(
                                                    self.module_name,
                                                    self.EXCHANGENAME,
                                                    'sspl_halon')

        if self.module_name == "RABBITMQEGRESSPROCESSOR":
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
        if self.module_name == "PLANECNTRLRMQEGRESSPROCESSOR":
            self._primary_rabbitmq_server   = conf_reader._get_value_with_default(
                                                        self.module_name, 
                                                        self.PRIMARY_RABBITMQ,
                                                        'localhost')
            self._secondary_rabbitmq_server = conf_reader._get_value_with_default(
                                                        self.module_name, 
                                                        self.SECONDARY_RABBITMQ,
                                                        'localhost')
        else:
            self._primary_rabbitmq_server   = "localhost"
            self._secondary_rabbitmq_server = "localhost"

        self._current_rabbitmq_server  = self._primary_rabbitmq_server

    def _toggle_rabbitmq_servers(self):
        """Toggle between hosts when a connection fails"""
        prev_host = self._current_rabbitmq_server
        if self._current_rabbitmq_server == self._primary_rabbitmq_server:
            self._current_rabbitmq_server = self._secondary_rabbitmq_server
        else:
            self._current_rabbitmq_server = self._primary_rabbitmq_server
        print "Warning! Connection timed out to %s attempting %s..." % (prev_host, self._current_rabbitmq_server)

    def addAuthFields(self, jsonMsg):
        """Adds authentication fields to message"""
 
        jsonMsg["username"] = self._signature_user
        jsonMsg["expires"]  = int(self._signature_expires)
        jsonMsg["time"]     = str(datetime.now())

        # Add a random uuid to last the lifetime of the msg
        self._request_uuid = str(uuid.uuid4())
        jsonMsg["message"]["sspl_ll_msg_header"]['uuid'] = self._request_uuid

        if use_security_lib:
            authn_token_len = len(self._signature_token) + 1
            session_length  = int(self._signature_expires)
            token = ctypes.create_string_buffer(SSPL_SEC.sspl_get_token_length())

            SSPL_SEC.sspl_generate_session_token(
                                self._signature_user, authn_token_len,
                                self._signature_token, session_length, token)
            # Generate the signature
            msg_len = len(str(jsonMsg)) + 1
            sig = ctypes.create_string_buffer(SSPL_SEC.sspl_get_sig_length())
            # Calculates the security signature and stores it in sig
            SSPL_SEC.sspl_sign_message(msg_len, str(jsonMsg), self._signature_user,
                                   token, sig)
            # Add the signature calculated using the SSPL_SEC security libs
            jsonMsg["signature"] = str(sig.raw)
        else:
            jsonMsg["signature"] = "SecurityLibNotInstalled"

    def basicPublish(self, jsonfile=None, message=None, wait_for_response=True, 
                     response_wait_time=3, force_wait=False, alldata=False, indent=False, 
                     remove_results_file=True, exchange=None, host=None):
        """Publishes message out to the rabbitmq server

        @param jsonfile = the file containing a json message to be sent to the server
        @type jsonfile = string
        @param message = A json message to be sent to the server
        @type message = string
        @param wait_for_response = flag denoting to wait for response or not
        @type wait_for_response = bool
        @param alldata = flag denoting to show all data received otherwise just the message section
        @type alldata = bool
        """

        if host is None:
            host = self._current_rabbitmq_server

        # If exchange is not passed in then use the one from the config file
        if exchange is None:
            exchange = self._exchangename

        self._alldata = alldata
        self._indent  = indent

        # Flag denoting a valid response message has been received
        self._msg_received = False
        self._request_uuid = None

        # Remove existing results.txt
        if remove_results_file:
            if os.path.exists("results.txt"):
                os.remove("results.txt")

        # Create rabbitMQ connection
        creds = pika.PlainCredentials(self._username, self._password)

        connection_success = False
        while not connection_success:
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters(
                     host=host, virtual_host=self._virtualhost, credentials=creds))
                connection_success = True
            except:
                self._toggle_rabbitmq_servers()
                time.sleep(10)

        channel = connection.channel()
        channel.exchange_declare(exchange=exchange,
                         type='topic', durable=self._durable)

        msg_props = pika.BasicProperties()
        msg_props.content_type = "text/plain"
        if jsonfile is not None:
            msg = open(jsonfile).read()

            #Convert msg to json format and add username, time til expire (seconds), current time, and security signature
            jsonMsg = json.loads(msg)

            #Add authentication fields to message
            self.addAuthFields(jsonMsg)

            #Validate the msg against the schemas
            self.validate(jsonMsg)

            #Convert the message back to plain text and send to consumer
            channel.basic_publish(exchange=exchange,
                                  routing_key=self._routingkey,
                                  properties=msg_props,
                                  body=str(json.dumps(jsonMsg, ensure_ascii=True).encode('utf8')))
            if not wait_for_response:
                print "Successfully transmitted request:"
            self._print_response(jsonMsg, save_to_file=False) 

        elif message is not None:
            # Convert the message back to plain text and send to consumer
            channel.basic_publish(exchange=exchange,
                                   routing_key=self._routingkey,
                                   properties=msg_props,
                                   body=str(message))
            if not wait_for_response:
                print "Successfully transmitted request"
                #self._print_response(message, save_to_file=False)     

        connection.close()
        del(connection)
 
        # Verify that we received a response back matching the uuid we sent in requeste
        if wait_for_response:
            print "Awaiting response(s)..."
            max_wait = 0
            while not self._msg_received:
                if force_wait:
                    time.sleep(response_wait_time)
                    break
                else:
                    time.sleep(1)
                max_wait += 1
                if max_wait > response_wait_time:
                    print "Timed out waiting for valid responses, giving up after {} seconds" \
                            .format(response_wait_time)
                    break


    def validate(self, jsonMsg):
        """Validate the json msg against one of the schemas"""

        # Get the incoming message type
        if jsonMsg.get("message").get("actuator_request_type") is not None:
            msgType = jsonMsg.get("message").get("actuator_request_type")

            # Validate against the actuator schema
            validate(jsonMsg, self._actuator_schema)

        elif jsonMsg.get("message").get("sensor_request_type") is not None:
            msgType = jsonMsg.get("message").get("sensor_request_type")

            # Validate against the sensor schema
            validate(jsonMsg, self._sensor_schema)

        else:
            # We only handle outgoing actuator and sensor requests, ignore everything else
            print "Only supports sending actuator and sensor requests"
            raise Exception("Validation failed")

    def _print_response(self, ingressMsg, save_to_file=True):
        """Print the ingress msg received on the rabbitMQ"""

        # If the alldata flag is set then use the entire ingressMsg otherwise just the message sections
        if self._alldata:
            response = ingressMsg
        else:
            if ingressMsg.get("message").get("actuator_response_type") is not None:
                response = ingressMsg.get("message").get("actuator_response_type")
            elif ingressMsg.get("message").get("sensor_response_type") is not None:
                response = ingressMsg.get("message").get("sensor_response_type")
            elif ingressMsg.get("message").get("sensor_request_type") is not None:
                response = ingressMsg.get("message").get("sensor_request_type")
            elif ingressMsg.get("message").get("actuator_request_type") is not None:
                response = ingressMsg.get("message").get("actuator_request_type")
            else:
                response = "Invalid response type received, should be actuator_response_type \
                       or sensor_response_type in: \n%s" % ingressMsg
                return

        # See if we should indent for readability
        if self._indent:
            response = json.dumps(response, sort_keys=True,
                             indent=4, separators=(',', ': '))
        print "%s\n" % str(response)

        # Write it out to a results file
        if save_to_file:
            res = "%s\n" % str(response).replace("\\n", "\n").replace("\\r", "")
            with open('results.txt', 'a+') as f:
                f.write(res)

    def _print_SEDresponse(self, ingressMsg):
        """Print responses from SED CLI"""
        ack_msg  = ingressMsg.get("message").get("actuator_response_type").get("ack").get("ack_msg")
        ack_type = ingressMsg.get("message").get("actuator_response_type").get("ack").get("ack_type")

        #print "ack_msg: %s" % ack_msg
        #print "ack_type: %s" % ack_type

        # Parse out hostname and raid values
        ack_types = ack_type.split(",")
        for value in ack_types:
            if "hostname" in value:
                hostname = value
            elif "command" in value:
                command = value
            elif "errors" in value:
                errors = value

        if hostname is None or \
           len(hostname) == 0:
           return

        print "\nResponse from %s" % (hostname)
        if len(errors) > 9:
            print "\nErrors%s" % errors

        # Handle 'drive status' response
        if "status" in command:
            template = "{0:^20}"
            rows = ack_msg.replace("-","").replace("{","").replace("}","").replace("'","").split("\n")
            first_row = True
            headers = ""
            for row in rows:
                header_fields = row.split(",")
                output = ""
                for header_field in header_fields:
                    if ":" in header_field:
                        fields = header_field.split(":")
                        # Grab the headers on the first row
                        if first_row == True:
                            headers = headers + template.format(fields[0]).upper()
                        output = output + template.format(fields[1])

                if first_row == True:
                    first_row = False
                    print headers
                print output
        else:
            print"Received response which is not yet handled by CLI. Please try again."
            sys.exit(1)


    def basicConsume(self):
        """Starts consuming all messages sent
        This function should be run on a daemon thread because it will never exit willingly
        Sets the thread event object to true and copies all ingress messages to self.interthread_msg
        """

        creds = pika.PlainCredentials(self._username, self._password)
        connection_success = False
        while not connection_success:
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters(
                    host=self._current_rabbitmq_server, virtual_host=self._virtualhost, credentials=creds))
                connection_success = True
            except:
                self._toggle_rabbitmq_servers()
                time.sleep(5)

        channel = connection.channel()
        channel.exchange_declare(exchange=self._exchangename,
                         type='topic', durable=self._durable)
        result = channel.queue_declare(exclusive=True)
        channel.queue_bind(exchange=self._exchangename,
                           queue=result.method.queue,
                           routing_key=self._routingkey)

        def callback(ch, method, properties, body):
            '''Called whenever a message is passed to the Consumer
            Verifies the authenticity of the signature with the SSPL_SEC libs
            Stores the message and alerts any waiting threads when an ingress message is processed
            '''
            ingressMsg = json.loads(body)

            uuid = None
            try:
                uuid = ingressMsg["message"]["sspl_ll_msg_header"]["uuid"]
            except KeyError:
                pass  # It's optional

            # Verify that the uuid of the response matches that of the request sent
            if self._request_uuid is not None and \
               uuid != self._request_uuid:
                print "Received a response on '{}' channel that doesn't match the request uuid:" \
                        .format(self._exchangename)
                print "Expected uuid: {} but received: {}".format(self._request_uuid, uuid)        
                self._print_response(ingressMsg, save_to_file=False)
                return

            username   = ingressMsg.get("username")
            signature  = ingressMsg.get("signature")
            message    = ingressMsg.get("message")
            msg_len    = len(message) + 1
            try:
                #Verifies the authenticity of an ingress message
                if use_security_lib:
                    assert(SSPL_SEC.sspl_verify_message(msg_len, str(message), username, signature) == 0)
            except:
                print "Authentication failed on message: %s" % ingressMsg

            try:
                #Sorts out any outgoing messages only processes *_response_type
                if ingressMsg.get("message").get("sensor_response_type") is not None or \
                    ingressMsg.get("message").get("actuator_response_type") is not None:
                    
                    # For debugging
                    if self.module_name == "RABBITMQEGRESSPROCESSOR":
                        self._total_msg_received += 1
                        print "%d) Received response on '%s' channel of queue '%s'" % \
                                (self._total_msg_received, self._exchangename, self._ingress_queue)
                        self._print_response(ingressMsg)
                        self._msg_received = True

                    # Plane controller SED CLI
                    elif self.module_name == "PLANECNTRLRMQEGRESSPROCESSOR":
                        self._print_SEDresponse(ingressMsg)
                        self._msg_received = True

            except Exception as e:
                print "Error printing response: %r" % e

            ch.basic_ack(delivery_tag = method.delivery_tag)

        # Sets the callback function to be used when start_consuming is called and specifies the queue to pull messages off of.
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
        
        connection_success = False
        while not connection_success:
            try:
                connection = pika.BlockingConnection(pika.ConnectionParameters(
                    host=self._current_rabbitmq_server, virtual_host=self._virtualhost, credentials=creds))
                connection_success = True
            except:
                time.sleep(5)

        channel = connection.channel()
        channel.exchange_declare(exchange=self._ackexchangename,
                         type='topic', durable=self._durable)
        result = channel.queue_declare(exclusive=True)
        channel.queue_bind(exchange=self._ackexchangename,
                           queue=result.method.queue,
                           routing_key=self._routingkey)

        def callback(ch, method, properties, body):
            '''Called whenever a message is passed to the Consumer
            Verifies the authenticity of the signature with the SSPL_SEC libs
            Stores the message and alerts any waiting threads when an ingress message is processed
            '''
            ingressMsg = json.loads(body)

            uuid = None
            try:
                uuid = ingressMsg["message"]["sspl_ll_msg_header"]["uuid"]
            except KeyError:
                pass  # It's optional

            # Verify that the uuid of the response matches that of the request sent
            if self._request_uuid is not None and \
               uuid != self._request_uuid:
                print "Received a Ack response on '{}' channel that doesn't match the request uuid:" \
                        .format(self._ackexchangename)
                print "Expected uuid: {} but received: {}".format(self._request_uuid, uuid)
                self._print_response(ingressMsg, save_to_file=False)
                return

            username   = ingressMsg.get("username")
            signature  = ingressMsg.get("signature")
            message    = ingressMsg.get("message")
            msg_len    = len(message) + 1
            try:
                # Verifies the authenticity of an ingress message
                if use_security_lib:
                    assert(SSPL_SEC.sspl_verify_message(msg_len, str(message), username, signature) == 0)
            except:
                print "Authentication failed on message: %s" % ingressMsg

            try:
                # Sorts out any outgoing messages only processes *_response_type
                if ingressMsg.get("message").get("sensor_response_type") is not None or \
                    ingressMsg.get("message").get("actuator_response_type") is not None:
                    self._total_ack_msg_received += 1
                    print "%s) Received on %s channel:" % \
                          (self._total_ack_msg_received, self._ackexchangename)
                    self._print_response(ingressMsg)
                    self._msg_received = True
            except Exception as e:
                print "Error printing response: %r" % e

            ch.basic_ack(delivery_tag = method.delivery_tag)

        # Sets the callback function to be used when start_consuming is called and specifies the queue to pull messages off of.
        channel.basic_consume(callback,
                              queue=result.method.queue)
        try:
          channel.start_consuming()
        except KeyboardInterrupt:
            channel.stop_consuming()
            
    def get_msg_received(self):
        return self._msg_received
