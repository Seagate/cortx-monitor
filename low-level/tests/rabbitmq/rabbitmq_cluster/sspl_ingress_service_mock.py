#!/usr/bin/env python3

import time

import pika

from pika import exceptions

all_hosts = [
    pika.URLParameters('amqp://ssc-vm-c-135'),
    pika.URLParameters('amqp://ssc-vm-c-136'),
]


def _get_new_connection():
    all_hosts.reverse()
    connection = pika.BlockingConnection(all_hosts)
    return connection


routing_key = 'msgs'


def send_msg(channel, msg):
    channel.basic_publish(
        exchange='amq.topic', routing_key=routing_key, body=msg,
        properties=pika.BasicProperties(delivery_mode=3),
    )


def _get_channel():
    connection = _get_new_connection()
    channel = connection.channel()
    channel.queue_declare('durable-queue', durable=True)
    channel.queue_bind(exchange='amq.topic', queue='durable-queue', routing_key=routing_key)
    return channel


count = 0


def _on_msg_received(ch, method, properties, body):
    global count
    count += 1
    print(f'Received {count} messages', end='\r')
    # print(" [x] %r:%r" % (method.routing_key, body))
    time.sleep(.5)


def consume():
    while True:
        try:
            channel = _get_channel()
            print(' [*] Waiting for logs. To exit press CTRL+C')
            channel.basic_consume(queue='durable-queue', on_message_callback=_on_msg_received, auto_ack=True)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            print('Connection closed, retrying...')
            continue
        except pika.exceptions.ChannelClosedByBroker:
            print('Broker closed connection, retrying...')
            continue
        except KeyboardInterrupt:
            print('Quiting...')
            break
    channel.close()


if __name__ == '__main__':
    consume()
