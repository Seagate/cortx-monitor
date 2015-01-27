#!/usr/bin/env python
import pika
import socket

fqdn = socket.gethostname()
shortHostname = fqdn.split(".")[0]
print("Using hostname: %s" % shortHostname)

creds = pika.PlainCredentials('sspluser', 'sspl4ever')
connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost', virtual_host='SSPL', credentials=creds))
channel = connection.channel()

channel.exchange_declare(exchange='sspl_bcast',
                         type='topic', durable=True)

result = channel.queue_declare(exclusive=False)
queue_name = result.method.queue

channel.queue_bind(exchange='sspl_bcast',
                   queue=shortHostname)

print ' [*] Waiting for json messages. To exit press CTRL+C'

def callback(ch, method, properties, body):
    print " [x] %r" % (body,)

channel.basic_consume(callback,
                      queue=shortHostname,
                      no_ack=True)

channel.start_consuming()
