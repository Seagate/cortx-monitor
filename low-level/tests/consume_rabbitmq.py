#!/usr/bin/env python
import pika
import socket
import json


creds = pika.PlainCredentials('sspluser', 'sspl4ever')
connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost', virtual_host='SSPL', credentials=creds))
channel = connection.channel()

channel.exchange_declare(exchange='sspl_bcast',
                         type='topic', durable=True)

result = channel.queue_declare(exclusive=True)
channel.queue_bind(exchange='sspl_bcast',
                   queue=result.method.queue,
		   routing_key='sspl_ll')
print ' [*] Waiting for json messages. To exit press CTRL+C'


def callback(ch, method, properties, body):
    ingressMsg = json.loads(body)

    # Get the message type
    if ingressMsg.get("monitor_msg_type") is not None:
        print " [x] %r" % (body,)


channel.basic_consume(callback,
                      queue=result.method.queue,
                      no_ack=True)
channel.start_consuming()

