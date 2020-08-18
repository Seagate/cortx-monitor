#!/usr/bin/env python3

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


import sys
import random
import time

import pika

from pika import exceptions

all_hosts = [
    pika.URLParameters('amqp://ssc-vm-c-135'),
    pika.URLParameters('amqp://ssc-vm-c-136'),
]


def _get_hosts():
    return random.shuffle(all_hosts)


def _get_new_connection():
    all_hosts.reverse()
    connection = pika.BlockingConnection(all_hosts)
    return connection


routing_key = 'msgs'


def send_msg(channel, msg):
    channel.basic_publish(
        exchange='amq.topic', routing_key=routing_key, body=msg,
        properties=pika.BasicProperties(delivery_mode=2),
    )


def _get_channel():
    connection = _get_new_connection()
    channel = connection.channel()
    channel.queue_declare('durable-queue', durable=True)
    channel.queue_bind(exchange='amq.topic', queue='durable-queue', routing_key=routing_key)
    return channel


def send_msgs(nos=1000):
    count = 0
    channel = _get_channel()
    while count < nos:
        message = 'Msg No: {}: '.format(count) + ' '.join(sys.argv[2:])
        try:
            send_msg(channel, message)
            print(" [x] Sent %r:%r" % (routing_key, message))
            time.sleep(.5)
        except pika.exceptions.AMQPConnectionError:
            print('Connection closed, retrying...')
            channel = _get_channel()
            continue
        count += 1
    channel.close()


if __name__ == '__main__':
    send_msgs(200)
