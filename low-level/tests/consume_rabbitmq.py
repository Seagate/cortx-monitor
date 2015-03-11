#!/usr/bin/env python
import pika
import json


creds = pika.PlainCredentials('sspluser', 'sspl4ever')
connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost', virtual_host='SSPL', credentials=creds))
channel = connection.channel()

channel.exchange_declare(exchange='sspl_halon',
                         type='topic', durable=False)

result = channel.queue_declare(exclusive=True)
channel.queue_bind(exchange='sspl_halon',
                   queue=result.method.queue,
		   routing_key='sspl_ll')
print ' [*] Waiting for json messages. To exit press CTRL+C'


def callback(ch, method, properties, body):
    ingressMsg = json.loads(body)

    # Get the message type
    if ingressMsg.get("monitor_msg_type") is not None or \
	ingressMsg.get("actuator_response_type") is not None:
        print " [x] %r" % (body,)

    ch.basic_ack(delivery_tag = method.delivery_tag)

channel.basic_consume(callback,
                      queue=result.method.queue)
channel.start_consuming()

