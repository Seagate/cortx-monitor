"""
 ****************************************************************************
 Filename:          plane_cntrl_ingress_processor.py
 Description:       Handles incoming messages for plane controller
                     via rabbitMQ over network
 Creation Date:     11/14/2016
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

from socket import gethostname

from jsonschema import Draft3Validator
from jsonschema import validate

from pika.exceptions import AMQPError

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS
from framework.utils.service_logging import logger
from framework.utils import encryptor
from framework.utils.amqp_factory import amqp_factory
from framework.amqp.plane_cntrl_egress_processor import PlaneCntrlEgressProcessor
from framework.base.sspl_constants import RESOURCE_PATH

from json_msgs.messages.actuators.ack_response import AckResponseMsg

import ctypes
try:
    use_security_lib=True
    SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')
except Exception as ae:
    logger.info("libsspl_sec not found, disabling authentication on ingress msgs")
    use_security_lib=False


class PlaneCntrlIngressProcessor(ScheduledModuleThread, InternalMsgQ):
    """Handles incoming messages via rabbitMQ over network"""

    MODULE_NAME = "PlaneCntrlIngressProcessor"
    PRIORITY    = 1

    # Section and keys in configuration file
    RABBITMQPROCESSOR   = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'
    QUEUE_NAME          = 'queue_name'
    ROUTING_KEY         = 'routing_key'
    VIRT_HOST           = 'virtual_host'
    USER_NAME           = 'username'
    PASSWORD            = 'password'
    PRIMARY_RABBITMQ    = 'primary_rabbitmq_server'
    SECONDARY_RABBITMQ  = 'secondary_rabbitmq_server'

    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Request.json"
    JSON_SENSOR_SCHEMA   = "SSPL-LL_Sensor_Request.json"
    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
    CLUSTER_ID_KEY = 'cluster_id'
    NODE_ID_KEY = 'node_id'
    RABBITMQ_CLUSTER_SECTION = 'RABBITMQCLUSTER'
    RABBITMQ_CLUSTER_HOSTS_KEY = 'cluster_nodes'

    @staticmethod
    def name():
        """ @return: name of the module."""
        return PlaneCntrlIngressProcessor.MODULE_NAME

    def __init__(self):
        super(PlaneCntrlIngressProcessor, self).__init__(self.MODULE_NAME,
                                                       self.PRIORITY)

        # Read in the actuator schema for validating messages
        #dir = os.path.dirname(__file__)
        #schema_file = os.path.join(dir, '..', '..', 'json_msgs',
        #                           'schemas', 'actuators',
        #                           self.JSON_ACTUATOR_SCHEMA)
        schema_file = os.path.join(RESOURCE_PATH + '/actuators',
                                   self.JSON_ACTUATOR_SCHEMA)
        self._actuator_schema = self._load_schema(schema_file)

        # Read in the sensor schema for validating messages
        #schema_file = os.path.join(dir, '..', '..', 'json_msgs',
        #                           'schemas', 'sensors',
        #                           self.JSON_SENSOR_SCHEMA)
        schema_file = os.path.join(RESOURCE_PATH + '/sensors',
                                    self.JSON_SENSOR_SCHEMA)
        self._sensor_schema = self._load_schema(schema_file)

    def _load_schema(self, schema_file):
        """Loads a schema from a file and validates

        @param string schema_file     location of schema on the file system
        @return string                Trimmed and validated schema
        """
        with open(schema_file, 'r') as f:
            schema = json.load(f)

        # Validate the schema to conform to Draft 3 specification
        Draft3Validator.check_schema(schema)

        return schema

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(PlaneCntrlIngressProcessor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(PlaneCntrlIngressProcessor, self).initialize_msgQ(msgQlist)

        self._current_rabbitMQ_server = None

        self._hostname = gethostname()

        self._read_config()

        # Get common amqp config
        amqp_config = self._get_default_amqp_config()
        self._comm = amqp_factory.get_amqp_consumer(**amqp_config)
        self._comm.init()

        # Display values used to configure pika from the config file
        self._log_debug("RabbitMQ user: %s" % self._username)
        self._log_debug("RabbitMQ exchange: %s, routing_key: %s, vhost: %s" %
                      (self._exchange_name, self._routing_key, self._virtual_host))

    def run(self):
        """Run the module periodically on its own thread."""
        #self._set_debug(True)
        #self._set_debug_persist(True)

        logger.info(f"{self.MODULE_NAME}, Initialization complete, accepting requests")

        try:
            # Start consuming and processing ingress msgs
            self._comm.consume(callback_fn=self._process_msg)
        except AMQPError as e:
            if self.is_running() is True:
                logger.info(f"{self.MODULE_NAME} ungracefully breaking out of run loop, restarting.")
                logger.exception(f"{self.MODULE_NAME}, AMQPError: {e}")
                self._toggle_rabbitMQ_servers()
                self._comm.init()
                self._scheduler.enter(10, self._priority, self.run, ())
            else:
                logger.info(f"{self.MODULE_NAME} gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, body):
        """Parses the incoming message and hands off to the appropriate module"""

        ingressMsg = {}
        try:
            if isinstance(body, dict) is False:
                ingressMsg = json.loads(body)
            else:
                ingressMsg = body

            # Authenticate message using username and signature fields
            username  = ingressMsg.get("username")
            signature = ingressMsg.get("signature")
            message   = ingressMsg.get("message")
            uuid      = message.get("sspl_ll_msg_header").get("uuid")
            msg_len   = len(message) + 1

            if uuid is None:
                uuid = "N/A"

            if use_security_lib and \
               SSPL_SEC.sspl_verify_message(msg_len, str(message), username, signature) != 0:
                logger.warn(f"{self.MODULE_NAME}, Authentication failed on message: {ingressMsg}")
                return

            # Get the incoming message type
            if message.get("actuator_request_type") is not None:
                msgType = message.get("actuator_request_type")

                # Validate against the actuator schema
                validate(ingressMsg, self._actuator_schema)

            elif message.get("sensor_request_type") is not None:
                msgType = message.get("sensor_request_type")

                # Validate against the sensor schema
                validate(ingressMsg, self._sensor_schema)

            else:
                # We only handle incoming actuator and sensor requests, ignore everything else
                return

            # Check for debugging being activated in the message header
            self._check_debug(message)
            self._log_debug("_process_msg, ingressMsg: %s" % ingressMsg)

            # Hand off to appropriate actuator message handler
            if msgType.get("plane_controller") is not None:
                command = message.get("actuator_request_type").get("plane_controller").get("command")

                # For a job status request forward over to PlaneCntrlEgressProcessor
                if command is not None and \
                   command == "job_status":
                    job_uuid = message.get("actuator_request_type").get("plane_controller").get("arguments").get("uuid", None)

                    node_id = None
                    if message.get("actuator_request_type").get("plane_controller").get("parameters") is not None and \
                       message.get("actuator_request_type").get("plane_controller").get("parameters").get("node_id") is not None:
                        node_id  = message.get("actuator_request_type").get("plane_controller").get("parameters").get("node_id")

                    # node_id set to None is a broadcast otherwise see if it applies to this node
                    if node_id is None or \
                       self._hostname in str(node_id):
                        self._process_job_status(uuid, job_uuid)
                else:
                    self._write_internal_msgQ("PlaneCntrlMsgHandler", message)

            # Handle restarting of internal threads
            elif msgType.get("thread_controller") is not None:
                node_id = None
                if message.get("actuator_request_type").get("thread_controller").get("parameters") is not None and \
                   message.get("actuator_request_type").get("thread_controller").get("parameters").get("node_id") is not None:
                    node_id = message.get("actuator_request_type").get("thread_controller").get("parameters").get("node_id", None)

                # node_id set to None is a broadcast otherwise see if it applies to this node
                if node_id is None or \
                   self._hostname in str(node_id):
                    self._write_internal_msgQ("ThreadController", message)

            # ... handle other incoming messages that have been validated
            else:
                # Log a msg about not being able to process the message
                logger.info(f"{self.MODULE_NAME}, _process_msg, unrecognized message: {str(ingressMsg)}")

        except Exception as ex:
            logger.exception(f"{self.MODULE_NAME}, _process_msg unrecognized message: {ingressMsg}")
            ack_msg = AckResponseMsg("Error Processing Msg", "Msg Handler Not Found", uuid).getJson()
            self._write_internal_msgQ(PlaneCntrlEgressProcessor.name(), ack_msg)

        # Acknowledge message was received
        self._comm.acknowledge()

    def _process_job_status(self, uuid, job_uuid):
        """Send the current job status requested"""
        self._log_debug("_process_job_status, job_status requested on uuid: %s" % job_uuid)
        try:
            # Get a copy of the job tasks in the PlaneCntrlMsgHandler msg queue pending being worked
            plane_cntrl_jobs = self._get_msgQ_copy("PlaneCntrlMsgHandler")
            response = "Not Found"

            # See if the requested uuid is in the list of pending jobs
            for plane_cntrl_job in plane_cntrl_jobs:
                self._log_debug("_process_job_status, plane_cntrl_job: %s" % str(plane_cntrl_job))
                if job_uuid in str(plane_cntrl_job):
                    response = "In Queue"
                    break

            ack_type = {}
            ack_type["hostname"] = gethostname()
            ack_type["command"]  = "job_status"
            ack_type["arguments"] = str(job_uuid)

            # The uuid is either not found or it's in the queue to be worked
            ack_msg = AckResponseMsg(json.dumps(ack_type), response, uuid).getJson()
            self._write_internal_msgQ(PlaneCntrlEgressProcessor.name(), ack_msg)
        except Exception as ex:
            logger.exception(f"{self.MODULE_NAME}, _process_job_status exception: {ex}")

    def _toggle_rabbitMQ_servers(self):
        """Toggle between hosts when a connection fails"""
        if self._current_rabbitMQ_server == self._primary_rabbitMQ_server:
            self._current_rabbitMQ_server = self._secondary_rabbitMQ_server
        else:
            self._current_rabbitMQ_server = self._primary_rabbitMQ_server

    def _read_config(self):
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')
            self._queue_name    = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.QUEUE_NAME,
                                                                 'ras_control')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.EXCHANGE_NAME,
                                                                 'ras_sspl')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ROUTING_KEY,
                                                                 'sspl_ll')
            self._username      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password      = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PASSWORD,
                                                                 'sspl4ever')
            self._hosts = self._conf_reader._get_value_list(self.RABBITMQ_CLUSTER_SECTION, 
                                COMMON_CONFIGS.get(self.RABBITMQ_CLUSTER_SECTION).get(self.RABBITMQ_CLUSTER_HOSTS_KEY))
            cluster_id = self._conf_reader._get_value_with_default(self.SYSTEM_INFORMATION_KEY,
                                                                   COMMON_CONFIGS.get(self.SYSTEM_INFORMATION_KEY).get(self.CLUSTER_ID_KEY),
                                                                   '')

            # Decrypt RabbitMQ Password
            decryption_key = encryptor.gen_key(cluster_id, ServiceTypes.RABBITMQ.value)
            self._password = encryptor.decrypt(decryption_key, self._password.encode('ascii'), self.RABBITMQPROCESSOR)


        except Exception as ex:
            logger.exception(f"{self.MODULE_NAME}, _read_config: {ex}")

    def _get_default_amqp_config(self):
        return {
                    "virtual_host": self._virtual_host,
                    "exchange": self._exchange_name,
                    "username": self._username,
                    "password": self._password,
                    "hosts": self._hosts,
                    "exchange_queue": self._queue_name,
                    "exchange_type": "topic",
                    "routing_key": self._routing_key,
                    "durable": True,
                    "exclusive": False,
                    "retry_count": 5,
                    "port": 5672
                }

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(PlaneCntrlIngressProcessor, self).shutdown()
        try:
            self._comm.stop()
        except pika.exceptions.ConnectionClosed:
            logger.info(f"{self.MODULE_NAME}, shutdown, RabbitMQ ConnectionClosed")
        except Exception as err:
            logger.info(f"{self.MODULE_NAME}, shutdown, RabbitMQ {err}")

