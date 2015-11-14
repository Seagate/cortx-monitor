#!/usr/bin/python
# -*- coding: utf-8 -*-

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

"""
Rabbit MQ messaging related common classes.
"""
# Third party
import pika
import json
# Local
from sspl_hl.utils.message_utils import NodeStatusResponse
# PLEX
from plex.core import log


class RabbitMQConfiguration(object):
    # pylint: disable=too-few-public-methods, too-many-instance-attributes

    """
    Class to define Rabbit-MQ configuration parameters.
    """

    def __init__(self, config_file_path):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """

        self.host = 'localhost'
        self.virtual_host = 'SSPL'
        self.username = 'sspluser'
        self.password = 'sspl4ever'
        self.exchange = 'sspl_hl_cmd'
        self.exchange_type = 'topic'
        self.exchange_queue = 'sspl_hl_cmd_resp'
        self.routing_key = 'sspl_hl_cmd_resp'
        if config_file_path:
            self.__dict__ = json.loads(open(config_file_path).read())


class HalondRMQ(RabbitMQConfiguration):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond Rabbit-MQ messaging.
    """

    def __init__(self, config_file_path):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """

        super(HalondRMQ, self).__init__(config_file_path)
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.host,
                virtual_host=self.virtual_host,
                credentials=pika.PlainCredentials(
                    self.username,
                    self.password)))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=self.exchange,
            type=self.exchange_type,
            durable=False)


class HalondConsumer(HalondRMQ):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond Rabbit-MQ consumer.
    """

    def __init__(self,
                 config_file_path,
                 callback_function):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """

        super(HalondConsumer, self).__init__(config_file_path)
        self._channel.queue_declare(queue=self.exchange_queue,
                                    exclusive=False)
        self._channel.queue_bind(exchange=self.exchange,
                                 queue=self.exchange_queue)
        self._channel.basic_consume(lambda ch, method, properties, body:
                                    callback_function(body),
                                    queue=self.exchange_queue,
                                    no_ack=True)

    def start_consuming(self):
        """
        Start consuming the queue messages.
        """
        self._channel.start_consuming()

    def stop_consuming(self):
        """
        Start consuming the queue messages.
        """
        self._channel.stop_consuming()
        self._connection.close()


class HalondPublisher(HalondRMQ):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond Rabbit-MQ publisher.
    """

    def __init__(self, config_file_path):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """
        super(HalondPublisher, self).__init__(config_file_path)

    def publish_message(self, message):
        """
        Publish the message to Halond Rabbit-MQ queue.

        @param message: message to be published to queue.
        @type message: str
        """
        self._channel.basic_publish(
            exchange=self.exchange,
            routing_key=self.routing_key,
            body=json.dumps(message))


class HalonRequestHandler(object):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond message request handler.
    """

    @staticmethod
    def process_request(body):
        """
        Process the message request received from the queue.
        """
        try:
            msg_dict = json.loads(body)
            message = msg_dict.get('message')
            message_id = find_key(message, "messageId")
            entity_type = find_key(message, "entityType")
            if entity_type == "node":
                node_response_dict = NodeStatusResponse(
                    ).get_response_message('node')
                set_value(node_response_dict['message'], "responseId",
                          message_id)
                return json.dumps(node_response_dict)
            return None
        except ValueError as value_error:
            print "Error: processing request:{}".format(value_error)
            return None


def find_key(message_dictionary, key):
    """
    Finds a key in dictionary <message_dictionary> if exists
    and return its value
    @param message_dictionary: Dictionary to look into
    @type message_dictionary: dict

    @param key: Key to get value of
    @type message_dictionary: str
    """

    if isinstance(message_dictionary, dict):
        if key in message_dictionary:
            return message_dictionary[key]
    return None


def set_value(message_dictionary, key, new_value):
    """
    Find a key if exists and set and return it's value
    @param message_dictionary: Dictionary to look into
    @type message_dictionary: Dictionary

    @param key: Key to update
    @type key: str

    @param new_value: New value for Key
    @type new_value: str
    """
    if isinstance(message_dictionary, dict):
        if key in message_dictionary:
            message_dictionary[key] = new_value
            return
        else:
            log.error("Key {} not found in message \
            dictionary {}".format(key, message_dictionary))
    else:
        log.error("message_dictionary argument must be a dictionary object")
