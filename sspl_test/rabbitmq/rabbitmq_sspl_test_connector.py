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

import pika
import pika.exceptions
import encodings.idna  # noqa

from sspl_test.framework.utils.service_logging import logger
from sspl_test.framework.utils.config_reader import ConfigReader
from cortx.utils.conf_store import Conf

RABBITMQCTL = '/usr/sbin/rabbitmqctl'

RABBITMQ_CLUSTER_SECTION = 'RABBITMQCLUSTER'
RABBITMQ_CLUSTER_HOSTS_KEY = 'cluster_nodes'

config = ConfigReader()
connection_exceptions = (
    pika.exceptions.AMQPConnectionError,
    pika.exceptions.ChannelClosedByBroker,
    pika.exceptions.ChannelWrongStateError,
)
connection_error_msg = (
    'RabbitMQ channel closed with error {}. Retrying with another host...'
)


# get_cluster_nodes method is 'depreciated' after product name change
# from LDR_R1 to LDR_R2. Refer EOS-8860. This method was used to get node names from
# rabbitmq cluster using rabbitmqctl command. Onwards LDR_R2, get_cluster_connection
# is used to get nodes from consul and create connections.
def get_cluster_nodes():
    process = subprocess.Popen(
        [f'{RABBITMQCTL} cluster_status'], stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, shell=True
    )
    stdout, stdin = process.communicate()
    for line in stdout.decode('utf-8').split('\n'):
        if 'running_nodes' in line:
            nodes = re.findall(r"rabbit@([-\w]+)", line)
            return nodes


def get_cluster_connection(username, password, virtual_host):
    """Makes connection with one of the rabbitmq node.
    """
    #hosts = get_cluster_nodes()  # Depreciated (EOS-8860)
    hosts = Conf.get("SSPL-Test", f"{RABBITMQ_CLUSTER_SECTION}>{RABBITMQ_CLUSTER_HOSTS_KEY}")
    if isinstance(hosts, str):
        hosts = hosts.strip().split(",")
    logger.debug(f'Cluster nodes [SSPL TEST]: {hosts}')
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
        self.connection = self._retry_connection()

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
            self._retry_connection()
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

    def _establish_connection(self):
        """Connects to a RabbitMQ node and binds the queues if available.
        """
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
