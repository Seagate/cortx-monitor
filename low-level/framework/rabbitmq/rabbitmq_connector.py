# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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

import time
import random
import subprocess
import re
import os
import pika
import pika.exceptions
import encodings.idna  # noqa

from framework.utils.service_logging import logger
from framework.utils.config_reader import ConfigReader
from framework.base.sspl_constants import COMMON_CONFIGS, component, CONSUL_HOST, CONSUL_PORT, SSPL_STORE_TYPE
from framework.utils.conf_utils import SSPL_CONF, Conf


RABBITMQ_CLUSTER_SECTION = 'RABBITMQCLUSTER'
RABBITMQ_CLUSTER_HOSTS_KEY = 'cluster_nodes'

# Onward LDR_R2, consul will be abstracted out and won't exist as hard dependency for SSPL
if SSPL_STORE_TYPE == 'consul':
    import consul
    host = os.getenv('CONSUL_HOST', CONSUL_HOST)
    port = os.getenv('CONSUL_PORT', CONSUL_PORT)
    consul_conn = consul.Consul(host=host, port=port)

config_reader = ConfigReader()
connection_exceptions = (
    pika.exceptions.AMQPConnectionError,
    pika.exceptions.ChannelClosedByBroker,
    pika.exceptions.ChannelWrongStateError,
    AttributeError
)
connection_error_msg = (
    'RabbitMQ channel closed with error {}. Retrying with another host...'
)


def get_cluster_connection(username, password, virtual_host):
    """Makes connection with one of the rabbitmq node.
    """
    hosts = ""
    if SSPL_STORE_TYPE == 'consul':
        consul_key = component + '/' + RABBITMQ_CLUSTER_SECTION + '/' + RABBITMQ_CLUSTER_HOSTS_KEY
        hosts = consul_conn.kv.get(consul_key)[1]["Value"].decode()
    else:
        hosts = Conf.get(SSPL_CONF, f"{RABBITMQ_CLUSTER_SECTION}>{RABBITMQ_CLUSTER_HOSTS_KEY}")
    if isinstance(hosts, str):
        hosts = hosts.strip().split(",")
    logger.debug(f'Cluster nodes: {hosts}')
    ampq_hosts = [
        f'amqp://{username}:{password}@{host}/{virtual_host}' for host in hosts
    ]
    ampq_hosts = [pika.URLParameters(host) for host in ampq_hosts]
    random.shuffle(ampq_hosts)
    connection = pika.BlockingConnection(ampq_hosts)
    return connection


class RabbitMQSafeConnection:
    """Class representing a safe RabbitMQ connection. Reconnects automatically
    if any rabbitmq operation fails due to connectivity issue. Also tries to
    complete the failed operation with the new connection.
    """

    def __init__(
        self,
        username,
        password,
        virtual_host,
        exchange_name,
        routing_key,
        queue_name,
    ):
        self.username = username
        self.password = password
        self.virtual_host = virtual_host
        self.exchange_name = exchange_name
        self.routing_key = routing_key
        self.queue_name = queue_name
        self.wait_time = 10
        self.connection = self._establish_connection(raise_err=False)

    def _retry_connection(self):
        """Retries to establish the connection until a connection is made
        with RabbitMQ a node in the cluster.
        """
        while True:
            try:
                self._establish_connection()
                logger.info('Connection established with RabbitMQ...')
                break
            except connection_exceptions as e:
                logger.error(connection_error_msg.format(repr(e)))
                logger.error('Connection closed while retrying...')
                time.sleep(self.wait_time)
            except Exception:
                raise

    def publish(self, exchange, routing_key, properties, body):
        """Publishes the message to the channel. If fails retries with
        a new connection.
        """
        try:
            self._channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                properties=properties,
                body=body,
            )
        except connection_exceptions as e:
            logger.error(connection_error_msg.format(e))
            logger.error(f'Connection closed while publising the message: {body}')
            self._establish_connection()
            self.publish(exchange, routing_key, properties, body)

    def consume(self, callback):
        """Consumes based on routing key. Retries if fails."""
        try:
            result = self._channel.queue_declare(queue="", exclusive=True)
            self._channel.queue_bind(
                exchange=self.exchange_name,
                queue=result.method.queue,
                routing_key=self.routing_key,
            )
            self._channel.basic_consume(
                on_message_callback=callback, queue=result.method.queue
            )
            self._channel.start_consuming()

        except connection_exceptions as e:
            logger.error(connection_error_msg.format(e))
            logger.error('Connection closed while consuming queue.')
            self._retry_connection()
            self.consume(callback)

    def ack(self, ch, delivery_tag):
        """Acknowledges the message on the channel. Retries on connection failure
        with a new RabbitMQ node.
        """
        try:
            self._channel.basic_ack(delivery_tag)
        except connection_exceptions as e:
            logger.error(f'Connection Ack error.: {repr(e)} Retrying...')
            self._retry_connection()
            self.ack(ch, delivery_tag)

    def _establish_connection(self, raise_err=True):
        """Connects to a RabbitMQ node and binds the queues if available.
        """
        try:
            self._connection = get_cluster_connection(
                self.username, self.password, self.virtual_host
            )
            self._channel = self._connection.channel()
            self._channel.exchange_declare(
                exchange=self.exchange_name, exchange_type='topic', durable=True
            )
            if self.queue_name:
                self._channel.queue_declare(queue=self.queue_name, durable=True)
                self._channel.queue_bind(
                    queue=self.queue_name,
                    exchange=self.exchange_name,
                    routing_key=self.routing_key,
                )
        except Exception as e:
            if raise_err:
                raise e

    def cleanup(self):
        """Cleans up the connection.
        """
        try:
            if self._connection is not None:
                self._channel.stop_consuming()
                self._channel.close()
                self._connection.close()
        except Exception as e:
            logger.error(f'Error closing RabbitMQ connection. {e}')
