#! /bin/python/
import json

import pika
import sys

from sspl_hl.utils.message_utils import FileSystemStatusQueryRequest


def generate_fs_status_req_msg():
    """ Generate a file system status request message from halon.
    """
    message = FileSystemStatusQueryRequest().get_request_message(
        "cluster", None
    )
    return json.dumps(message)


class HalonReqRespHandler(object):
    """
    """

    V_HOST = 'SSPL'
    USERNAME = 'sspluser'
    PWD = 'sspl4ever'

    @staticmethod
    def publish_halon_msg(message=None):
        """
        """

        EXCHANGE = 'sspl_hl_cmd'
        ROUTING_KEY = 'sspl_hl_cmd'

        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost',
            virtual_host=HalonReqRespHandler.V_HOST,
            credentials=pika.PlainCredentials(
                HalonReqRespHandler.USERNAME,
                HalonReqRespHandler.PWD)))
        channel = connection.channel()
        print ' [x] Connection is UP and channel is created!'

        channel.exchange_declare(exchange=EXCHANGE,
                                 type='topic')
        print ' [x] Exchange: {} is declared and ready'.format(EXCHANGE)
        msg = message or 'Hello World!'
        channel.basic_publish(exchange=EXCHANGE,
                              routing_key=ROUTING_KEY,
                              body=msg)
        print(" [x] Sent %r:%r" % (ROUTING_KEY, msg))
        connection.close()

    @staticmethod
    def subscribe_halon_response():
        """
        """
        EXCHANGE = 'sspl_hl_resp'
        QUEUE = 'sspl_hl_resp'
        ROUTING_KEY = 'sspl_hl_resp'

        connection = pika.BlockingConnection(pika.ConnectionParameters(
            host='localhost',
            virtual_host=HalonReqRespHandler.V_HOST,
            credentials=pika.PlainCredentials(
                HalonReqRespHandler.USERNAME,
                HalonReqRespHandler.PWD)))
        channel = connection.channel()
        print ' [x] Connection is UP and channel is created!'
        # channel.exchange_declare(exchange=EXCHANGE,
        #                        type='topic')
        print ' [x] Exchange: {} is declared and ready'.format(EXCHANGE)
        channel.queue_declare(queue=QUEUE)
        # queue_name = result.method.queue

        channel.queue_bind(exchange=EXCHANGE,
                           queue=QUEUE,
                           routing_key=ROUTING_KEY)

        print(' [*] Waiting for logs. To exit press CTRL+C')

        def callback(ch, method, properties, body):
            print(" [x] %r:%r" % (method.routing_key, body))

        channel.basic_consume(callback,
                              queue=QUEUE,
                              no_ack=True)
        channel.start_consuming()


if len(sys.argv) > 1:
    HalonReqRespHandler.subscribe_halon_response()
else:
    try:
        msg = generate_fs_status_req_msg()
        HalonReqRespHandler.publish_halon_msg(msg)
    except KeyboardInterrupt:
        print 'Ctrl has been pressed.'
