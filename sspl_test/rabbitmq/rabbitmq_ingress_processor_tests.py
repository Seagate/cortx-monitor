# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

"""
 ****************************************************************************
  Description:       Handles incoming messages via rabbitMQ for automated tests
 ****************************************************************************
"""

import json
import os
import time
import socket

from jsonschema import Draft3Validator
from jsonschema import validate

from cortx.utils.message_bus import MessageConsumer

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import RESOURCE_PATH

from framework.utils.conf_utils import (CLUSTER, SRVNODE,
                                        Conf, SSPL_TEST_CONF)
import ctypes
from . import message_bus, producer_initialized

SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')


class RabbitMQingressProcessorTests(ScheduledModuleThread, InternalMsgQ):
    """Handles incoming messages via rabbitMQ for automated tests"""

    MODULE_NAME = "RabbitMQingressProcessorTests"
    PRIORITY = 1

    # Section and keys in configuration file
    RABBITMQPROCESSORTEST = MODULE_NAME.upper()
    CONSUMER_ID = "consumer_id"
    CONSUMER_GROUP = "consumer_group"
    MESSAGE_TYPE = "message_type"
    OFFSET = "offset"
    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
    CLUSTER_ID_KEY = 'cluster_id'
    NODE_ID_KEY = 'node_id'
    CLUSTER_ID_KEY = "cluster_id"

    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Response.json"
    JSON_SENSOR_SCHEMA = "SSPL-LL_Sensor_Response.json"

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RabbitMQingressProcessorTests.MODULE_NAME

    def __init__(self):
        super(RabbitMQingressProcessorTests, self).__init__(self.MODULE_NAME,
                                                            self.PRIORITY)

        # Read in the actuator schema for validating messages
        fileName = os.path.join(RESOURCE_PATH + '/actuators',
                                self.JSON_ACTUATOR_SCHEMA)

        self._actuator_schema = self._load_schema(fileName)

        # Read in the sensor schema for validating messages
        fileName = os.path.join(RESOURCE_PATH + '/sensors',
                                self.JSON_SENSOR_SCHEMA)

        self._sensor_schema = self._load_schema(fileName)

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

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(RabbitMQingressProcessorTests, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RabbitMQingressProcessorTests, self).initialize_msgQ(msgQlist)

        self._read_config()

        producer_initialized.wait()
        self._consumer = MessageConsumer(message_bus,
                                         consumer_id=self._consumer_id,
                                         consumer_group=self._consumer_group,
                                         message_types=[self._message_type],
                                         auto_ack=False, offset=self._offset)

    def run(self):
        # self._set_debug(True)
        # self._set_debug_persist(True)

        # time.sleep(180)
        logger.info(
            "RabbitMQingressProcessor, Initialization complete, accepting requests")

        try:
            while True:
                message = self._consumer.receive()
                if message:
                    logger.info(
                        f"RabbitMQingressProcessor, Message Recieved: {message}")
                    self._process_msg(message)
                    # Acknowledge message was received
                    self._consumer.ack()
                else:
                    time.sleep(1)
        except Exception as e:
            if self.is_running() is True:
                logger.info(
                    "RabbitMQingressProcessor ungracefully breaking out of run loop, restarting.")
                logger.error("RabbitMQingressProcessor, Exception: %s" % str(e))
                self._scheduler.enter(10, self._priority, self.run, ())
            else:
                logger.info(
                    "RabbitMQingressProcessor gracefully breaking out of run Loop, not restarting.")

        self._log_debug("Finished processing successfully")

    def _process_msg(self, body):
        """Parses the incoming message and hands off to the appropriate module"""

        self._log_debug("_process_msg, body: %s" % body)

        ingressMsg = {}
        try:
            if isinstance(body, dict) is False:
                ingressMsg = json.loads(body)
            else:
                ingressMsg = body

            # Authenticate message using username and signature fields
            username = ingressMsg.get("username")
            signature = ingressMsg.get("signature")
            message = ingressMsg.get("message")

            assert (username is not None)
            assert (signature is not None)
            assert (message is not None)

            msg_len = len(message) + 1

            if SSPL_SEC.sspl_verify_message(msg_len, str(message), username,
                                            signature) != 0:
                logger.error(
                    "Authentication failed on message: %s" % ingressMsg)
                return

            # We're acting as HAlon so ignore actuator_requests
            #  and sensor_requests messages
            if message.get("actuator_request_type") is not None or \
                    message.get("sensor_request_type") is not None:
                return

            # Get the message type
            msgType = message.get("actuator_response_type")

            # If it's an incoming actuator msg then validate against
            #  Actuator Response schema
            if msgType is not None:
                validate(ingressMsg, self._actuator_schema)

            if msgType is None:
                msgType = message.get("sensor_response_type")
                validate(ingressMsg, self._sensor_schema)

                # Ignore drive status messages when thread starts up during tests
                if message.get("sensor_response_type").get(
                        "disk_status_drivemanager") is not None:
                    return
            # If the message comes from other SSPL hosts, do not pass that
            # message to internal queue. This happens as SSPL instances are
            # listening to common queues in a RabbitMQ cluster.
            if 'host_id' in msgType and socket.getfqdn() != msgType['host_id']:
                return
            # Write to the msg queue so the lettuce tests can
            #  retrieve it and examine for accuracy during automated testing
            self._write_internal_msgQ("RabbitMQingressProcessorTests", message)

        except Exception as ex:
            logger.exception(
                "_process_msg unrecognized message: %r" % ingressMsg)

    def _read_config(self):
        """Configure the RabbitMQ exchange with defaults available"""
        # Make methods locally available
        self._node_id = Conf.get(SSPL_TEST_CONF,
                                 f"{CLUSTER}>{SRVNODE}>{self.NODE_ID_KEY}",
                                 'SN01')
        self._consumer_id = Conf.get(SSPL_TEST_CONF,
                                     f"{self.RABBITMQPROCESSORTEST}>{self.CONSUMER_ID}",
                                     'sspl_actuator')
        self._consumer_group = Conf.get(SSPL_TEST_CONF,
                                        f"{self.RABBITMQPROCESSORTEST}>{self.CONSUMER_GROUP}",
                                        'cortx_monitor')
        self._message_type = Conf.get(SSPL_TEST_CONF,
                                      f"{self.RABBITMQPROCESSORTEST}>{self.MESSAGE_TYPE}",
                                      'Requests')
        self._offset = Conf.get(SSPL_TEST_CONF,
                                f"{self.RABBITMQPROCESSORTEST}>{self.OFFSET}",
                                'earliest')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQingressProcessorTests, self).shutdown()
