#!/usr/bin/python3

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

"""Writes json message to RabbitMQ channel"""

import os
import pika
import sys
import json

VIRTUAL_HOST = 'SSPL'
EXCHANGE_NAME = 'sspl-in'
USERNAME = 'sspluser'
PASSWORD = 'sspl4ever'
RABBITMQ_HOST = 'localhost'
QUEUE = 'actuator-req-queue'
EXCHANGE_TYPE = 'topic'
ROUTING_KEY = 'actuator-req-key'

def usage():
    sys.stderr.write('usage: %s <sensor_type> <identifier> <status>\n' %sys.argv[0])
    sys.stderr.write('where:\n    sensor - sensor message type e.g. disk_status_drivemanager\n')
    sys.stderr.write('    identifier - serial/identifier for the object\n')
    sys.stderr.write('    status - status for the identifier\n')
    sys.exit(1)

def get_connection():
    """Returns a new created connections"""

    creds = pika.PlainCredentials(USERNAME, PASSWORD)
    connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=RABBITMQ_HOST, virtual_host=VIRTUAL_HOST, credentials=creds))
    channel = connection.channel()
    result = channel.queue_declare(queue=QUEUE, durable=True)
    channel.exchange_declare(exchange=EXCHANGE_NAME, type=EXCHANGE_TYPE, durable=True)
    channel.queue_bind(queue=QUEUE, exchange=EXCHANGE_NAME, routing_key=ROUTING_KEY)
    return channel

def send_message(channel, msg):
    """Publishes <msg> on RabbitMQ <channel>."""

    msg_props = pika.BasicProperties()
    msg_props.content_type = "text/plain"
    channel.basic_publish(exchange=EXCHANGE_NAME, routing_key=ROUTING_KEY, properties=msg_props, body=str(msg))

def prepare_msg_raid_data(msg, identifier, status):
    if len(ids) != 2: raise Exception('invalid identifier for raid_data')
    sts = status.split(':')
    if len(sts) != 2: raise Exception('invalid status for raid_data')

    msg = msg.replace('SSPL_MOCK_ID_1', ids[0])
    msg = msg.replace('SSPL_MOCK_ID_2', ids[1])
    msg = msg.replace('SSPL_MOCK_STATUS_1', sts[0])
    msg = msg.replace('SSPL_MOCK_STATUS_2', sts[1])
    return msg

def prepare_msg_disk_status_hpi(msg, identifier, status):

    msg = msg.replace('SSPL_MOCK_ID', identifier)
    sts = status.split(':')
    if len(sts) != 2: raise Exception('invalid status for raid_data')

    msg = msg.replace('SSPL_MOCK_STATUS_1', sts[0])
    msg = msg.replace('SSPL_MOCK_STATUS_2', sts[1])

    return msg

def prepare_msg_default(msg, identifier, status):
    msg = msg.replace('SSPL_MOCK_ID', identifier)
    msg = msg.replace('SSPL_MOCK_STATUS', status)
    return msg

def prepare_msg(sensor, identifier, status):
    msg = open(msg_file).read()
    helper = {
        'raid_data': prepare_msg_raid_data,
        'disk_status_hpi': prepare_msg_disk_status_hpi,
        'disk_status_drivermanager': prepare_msg_default,
    }

    if sensor in helper.keys():
        msg = helper[sensor](msg, identifier, status)
    else:
        msg = prepare_msg_default(msg, identifier, status)

    return msg

if __name__ == "__main__":
    if len(sys.argv) < 4: usage()
    sensor, identifier, status = sys.argv[1], sys.argv[2], sys.argv[3]

    msg_file = os.path.join(os.path.dirname(sys.argv[0]), sensor)
    if not os.path.exists(msg_file):
        sys.stderr.write('error: invalid sensor type\n')
        usage()

    try:
        #msg = prepare_msg(sensor, identifier, status)
        msg = ''' {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "2015-05-29 14:28:30.974749",
        "expires" : 500,

        "message" : {
            "sspl_ll_msg_header": {
                "schema_version": "1.0.0",
                "sspl_version": "1.0.0",
                "msg_version": "1.0.0"
            },
             "sspl_ll_debug": {
                "debug_component" : "sensor",
                "debug_enabled" : true
            },
            "sensor_request_type": {
                "node_data": {
                    "sensor_type": "node:os:memory_usage"
                }
            }
        }
    }'''
        channel = get_connection()
        if channel: send_message(channel, msg)

    except Exception as e:
        print('error: Could not send mesasge. %s' % e)
