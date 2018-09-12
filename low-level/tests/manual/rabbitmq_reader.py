#!/usr/bin/env python

import sys
import pika
import json
import pprint

SSPL_USER = "sspluser"
SSPL_PASS = "sspl4ever"
SSPL_VHOST = "SSPL"

def process_msg(ch, method, properties, body):
    print body

try:
    if len(sys.argv) <= 1:
        print("usage: %s <exchange> <queue> <key>\n")
        sys.exit(1)

    SSPL_EXCHANGE = sys.argv[1]
    SSPL_QUEUE = sys.argv[2]
    SSPL_KEY = sys.argv[3]

    creds = pika.PlainCredentials(SSPL_USER, SSPL_PASS)
    connection = pika.BlockingConnection(pika.\
        ConnectionParameters(host="localhost", virtual_host=SSPL_VHOST, credentials=creds))
    channel = connection.channel()
    result = channel.queue_declare(queue=SSPL_QUEUE, durable=True)
    channel.exchange_declare(exchange=SSPL_EXCHANGE, type='topic', durable=True)
    channel.queue_bind(queue=SSPL_QUEUE, exchange=SSPL_EXCHANGE, routing_key=SSPL_KEY)
    channel.basic_consume(process_msg, queue=result.method.queue)
    channel.start_consuming()

except Exception as e:
    print e
