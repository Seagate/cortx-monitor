#!/usr/bin/python3.6

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
import pika
import json
import pprint

SSPL_USER = "sspluser"
SSPL_PASS = "sspl4ever"
SSPL_VHOST = "SSPL"

def process_msg(ch, method, properties, body):
    print(body.decode())

try:
    if len(sys.argv) <= 2 or len(sys.argv) > 3:
        print("usage: %s <exchange> <key>\n")
        sys.exit(1)

    SSPL_EXCHANGE = sys.argv[1]
    SSPL_KEY = sys.argv[2]

    creds = pika.PlainCredentials(SSPL_USER, SSPL_PASS)
    connection = pika.BlockingConnection(pika.\
        ConnectionParameters(host="localhost", virtual_host=SSPL_VHOST, credentials=creds))
    channel = connection.channel()
    result = channel.queue_declare(queue="", exclusive=True)
    channel.exchange_declare(exchange=SSPL_EXCHANGE, exchange_type='topic', durable=True)
    channel.queue_bind(queue=result.method.queue, exchange=SSPL_EXCHANGE, routing_key=SSPL_KEY)
    channel.basic_consume(on_message_callback=process_msg, queue=result.method.queue)
    channel.start_consuming()

except Exception as e:
    print(e)
