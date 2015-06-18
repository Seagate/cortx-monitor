#!/usr/bin/env python
import json
import pika
import socket

creds = pika.PlainCredentials('sspluser', 'sspl4ever')
connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost', virtual_host='SSPL', credentials=creds))
channel = connection.channel()

channel.exchange_declare(exchange='sspl_halon',
                         type='topic', durable=False)

msg_props = pika.BasicProperties()
msg_props.content_type = "text/plain"

jsonMsg = open("actuator_msgs/sensor_request_cpu_data.json").read()

channel.basic_publish(exchange='sspl_halon',
                      routing_key='sspl_ll',
                      properties=msg_props,
                      body=str(jsonMsg))

print "Successfully Sent: %s" % jsonMsg

connection.close()
del(connection)




