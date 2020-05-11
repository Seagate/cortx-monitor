"""
 ****************************************************************************
 Filename:          rabbitmq_egress_accumulated_msgs_processor.py
 Description:       This processor handles acuumalted messages in consul
                    This keeps on running periodicaly and check if there is
                    any message to be sent to rabbtmq. If rabbitmq connection
                    is availble message will be sent, else in next iteration
                    it will be retried.
 Creation Date:     03/19/2020
 Author:            Sandeep Anjara

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by
 Seagate Technology, LLC.
 ****************************************************************************
"""
import sys

import pika
import json
import time

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ

from framework.utils.service_logging import logger

from framework.rabbitmq.rabbitmq_connector import RabbitMQSafeConnection, connection_exceptions, connection_error_msg
from framework.utils import encryptor
from framework.utils.store_factory import store
from framework.utils.store_queue import store_queue
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS


class RabbitMQEgressAccumulatedMsgsProcessor(ScheduledModuleThread, InternalMsgQ):
    """Send any unsent message to rabbitmq"""

    SENSOR_NAME = "RabbitMQEgressAccumulatedMsgsProcessor"
    PRIORITY    = 1

    #TODO: read egress config from comman place
    # Section and keys in configuration file
    RABBITMQPROCESSOR       = 'RABBITMQEGRESSPROCESSOR'
    VIRT_HOST               = 'virtual_host'

    PRIMARY_RABBITMQ_HOST   = 'primary_rabbitmq_host'
    EXCHANGE_NAME           = 'exchange_name'
    QUEUE_NAME              = 'queue_name'
    ROUTING_KEY             = 'routing_key'

    ACK_QUEUE_NAME          = 'ack_queue_name'
    ACK_ROUTING_KEY         = 'ack_routing_key'

    USER_NAME               = 'username'
    PASSWORD                = 'password'
    SIGNATURE_USERNAME      = 'message_signature_username'
    SIGNATURE_TOKEN         = 'message_signature_token'
    SIGNATURE_EXPIRES       = 'message_signature_expires'
    IEM_ROUTE_ADDR          = 'iem_route_addr'
    IEM_ROUTE_EXCHANGE_NAME = 'iem_route_exchange_name'

    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
    CLUSTER_ID_KEY = 'cluster_id'
    NODE_ID_KEY = 'node_id'
    # 300 seconds for 5 mins
    MSG_TIMEOUT = 300


    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RabbitMQEgressAccumulatedMsgsProcessor.SENSOR_NAME

    def __init__(self):
        super(RabbitMQEgressAccumulatedMsgsProcessor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread
        super(RabbitMQEgressAccumulatedMsgsProcessor, self).initialize(conf_reader)

        super(RabbitMQEgressAccumulatedMsgsProcessor, self).initialize_msgQ(msgQlist)

        self._read_config()

        self._connection = RabbitMQSafeConnection(
            self._username, self._password, self._virtual_host,
            self._exchange_name, self._routing_key, self._queue_name
        )

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""
        logger.debug("Consul accumulated messages processing started")
        if not self._is_my_msgQ_empty():
            # Check for shut down message from sspl_ll_d and set a flag to shutdown
            #  once our message queue is empty
            self._jsonMsg, _ = self._read_my_msgQ()
            if self._jsonMsg.get("message").get("actuator_response_type") is not None and \
                self._jsonMsg.get("message").get("actuator_response_type").get("thread_controller") is not None and \
                self._jsonMsg.get("message").get("actuator_response_type").get("thread_controller").get("thread_response") == \
                    "SSPL-LL is shutting down":
                    logger.info("RabbitMQEgressAccumulatedMsgsProcessor, run, received" \
                                    "global shutdown message from sspl_ll_d")
                    self.shutdown()
        try:
            if not store_queue.is_empty():
                logger.debug("Found accumulated messages, trying to send again")
                self._connection._establish_connection()
                msg_props = pika.BasicProperties()
                msg_props.content_type = "text/plain"
                while not store_queue.is_empty():
                    message = store_queue.get()
                    dict_msg = json.loads(message)
                    if "actuator_response_type" in dict_msg["message"]:
                        event_time = dict_msg["message"]["actuator_response_type"]["info"]["event_time"]
                        time_diff = int(time.time()) - int(event_time)
                        if time_diff > self.MSG_TIMEOUT:
                            continue
                    self._connection.publish(exchange=self._exchange_name,routing_key=self._routing_key,properties=msg_props,body=message)

                self._connection.cleanup()
        except connection_exceptions as e:
            logger.error(connection_error_msg.format(e))
        finally:
            logger.debug("Consul accumulated processing ended")
            self._scheduler.enter(30, self._priority, self.run, ())

    def _read_config(self):
        """Configure the RabbitMQ exchange with defaults available"""
        try:
            self._virtual_host  = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.VIRT_HOST,
                                                                 'SSPL')

            # Read common RabbitMQ configuration
            self._primary_rabbitmq_host = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PRIMARY_RABBITMQ_HOST,
                                                                 'localhost')

            # Read RabbitMQ configuration for sensor messages
            self._queue_name    = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.QUEUE_NAME,
                                                                 'sensor-queue')
            self._exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.EXCHANGE_NAME,
                                                                 'sspl-out')
            self._routing_key   = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ROUTING_KEY,
                                                                 'sensor-key')
            # Read RabbitMQ configuration for Ack messages
            self._ack_queue_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ACK_QUEUE_NAME,
                                                                 'sensor-queue')
            self._ack_routing_key = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.ACK_ROUTING_KEY,
                                                                 'sensor-key')

            self._username = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.USER_NAME,
                                                                 'sspluser')
            self._password = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.PASSWORD,
                                                                 '')
            self._signature_user = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_USERNAME,
                                                                 'sspl-ll')
            self._signature_token = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_TOKEN,
                                                                 'FAKETOKEN1234')
            self._signature_expires = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.SIGNATURE_EXPIRES,
                                                                 "3600")
            self._iem_route_addr = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.IEM_ROUTE_ADDR,
                                                                 '')
            self._iem_route_exchange_name = self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                 self.IEM_ROUTE_EXCHANGE_NAME,
                                                                 'sspl-in')

            cluster_id = self._conf_reader._get_value_with_default(self.SYSTEM_INFORMATION_KEY,
                                                                   COMMON_CONFIGS.get(self.SYSTEM_INFORMATION_KEY).get(self.CLUSTER_ID_KEY),
                                                                   '')

            # Decrypt RabbitMQ Password
            decryption_key = encryptor.gen_key(cluster_id, ServiceTypes.RABBITMQ.value)
            self._password = encryptor.decrypt(decryption_key, self._password.encode('ascii'), "RabbitMQEgressAccumulatedMsgsProcessor")

            if self._iem_route_addr != "":
                logger.info("         Routing IEMs to host: %s" % self._iem_route_addr)
                logger.info("         Using IEM exchange: %s" % self._iem_route_exchange_name)
        except Exception as ex:
            logger.error("RabbitMQegressProcessor, _read_config: %r" % ex)


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RabbitMQEgressAccumulatedMsgsProcessor, self).shutdown()
        self._connection.cleanup()
