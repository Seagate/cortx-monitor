#!/usr/bin/env python2.7
"""
Utility classes for Rabbit MQ messaging.
"""

# Standard
import json

# Thrid party
import pika

# Local
from sspl_hl.utils.message_utils import NodeStatusResponse


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
            config_fd = open(config_file_path)
            self.__dict__ = json.loads(config_fd.read())
            config_fd.close()


class FakeHalondRMQ(object):
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
        self.config = RabbitMQConfiguration(config_file_path)
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.config.host,
                virtual_host=self.config.virtual_host,
                credentials=pika.PlainCredentials(
                    self.config.username,
                    self.config.password)))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=self.config.exchange,
            type=self.config.exchange_type,
            durable=False)


class FakeHalondConsumer(FakeHalondRMQ):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond Rabbit-MQ consumer.
    """

    def __init__(self, config_file_path, callback_function):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """
        super(FakeHalondConsumer, self).__init__(config_file_path)
        self._channel.queue_declare(
            queue=self.config.exchange_queue,
            exclusive=True)
        self._channel.queue_bind(
            exchange=self.config.exchange,
            queue=self.config.exchange_queue)
        self._channel.basic_consume(
            lambda ch, method, properties, body:
            callback_function(body),
            queue=self.config.exchange_queue,
            no_ack=True
        )

    def start_consuming(self):
        """
        Start consuming the queue messages.
        """
        self._channel.start_consuming()


class FakeHalondPublisher(FakeHalondRMQ):
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
        super(FakeHalondPublisher, self).__init__(config_file_path)

    def publish_message(self, message):
        """
        Publish the message to Halond Rabbit-MQ queue.

        @param message: message to be published to queue.
        @type message: str
        """
        self._channel.basic_publish(
            exchange=self.config.exchange,
            routing_key=self.config.routing_key,
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
            message_id = HalonRequestHandler.find_key(msg_dict, "messageId")
            entity_type = HalonRequestHandler.find_key(msg_dict, "entityType")
            if entity_type == "node":
                node_response_dict = NodeStatusResponse().get_response_message(
                    "node")
                HalonRequestHandler.set_value(
                    d=node_response_dict,
                    key="messageId",
                    new_value=message_id
                )
                return json.dumps(node_response_dict)
            return None
        except ValueError as value_error:
            print "Error: processing request:{}".format(value_error)
            return None

    @staticmethod
    def find_key(d, key):
        """
        Finds a key in dictionary <d> if exists
        and return its value
        @param d: Dictionary to look into
        @type d: dict

        @param key: Key to get value of
        @type d: str
        """
        if isinstance(d, dict):
            if key in d:
                return d[key]
            for k, v in d.items():
                if isinstance(v, dict):
                    item = HalonRequestHandler.find_key(v, key)
                    if item is not None:
                        return item
        else:
            return None

    @staticmethod
    def set_value(d, key, new_value):
        """
        Find a key if exists and set and return it's value
        @param d: Dictionary to look into
        @type d: Dictionary

        @param key: Key to update
        @type d: str

        @param new_value: New value for Key
        @type d: str
        """
        if isinstance(d, dict):
            if key in d:
                d[key] = new_value
                return d[key]
            for k, v in d.items():
                if isinstance(v, dict):
                    item = HalonRequestHandler.set_value(
                        v,
                        key,
                        new_value)
                    if item is not None:
                        d[key] = new_value
                        return d[key]
            return None
