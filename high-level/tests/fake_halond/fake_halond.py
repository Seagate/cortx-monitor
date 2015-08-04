#!/usr/bin/env python2.7
"""
A fake halond that listens to rabbitmq for messages and then just dumps them
out to a directory in the order in which they're received.

Usage::
    ./fake_halond.py [-d /tmp/fake_halond]

The files in the directory will be named numerically.  ie the first message
will be named 1.json, the second 2.json, the 10th 10.json.  The directory (and
all files within it) will be deleted when the process exits.
"""

import os.path
import shutil
import pika
import argparse
import signal
import sys
import json


def _cleanup(cleanup_funcs):
    """ Signal handler to perform cleanup and exit. """
    for func in cleanup_funcs:
        func()
    sys.exit(1)


class RabbitMQConfiguration(object):
    # pylint: disable=too-few-public-methods, too-many-instance-attributes

    """
    Class to define Rabbit-MQ configuration parameters.
    """

    def __init__(self, config_file_path):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """
        self.host = 'localhost'
        self.virtual_host = 'SSPL'
        self.username = 'sspluser'
        self.password = 'sspl4ever'
        self.exchange = 'sspl_hl_cmd'
        self.exchange_type = 'topic'
        self.exchange_queue = 'sspl_hl_cmd'
        self.routing_key = 'sspl_hl_cmd'
        if config_file_path:
            self.__dict__ = json.loads(open(config_file_path).read())


class FakeHalondRMQ(object):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond Rabbit-MQ messaging.
    """

    def __init__(self, config_file_path):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """
        self.rabbit_mq_config = RabbitMQConfiguration(config_file_path)
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=self.rabbit_mq_config.host,
                virtual_host=self.rabbit_mq_config.virtual_host,
                credentials=pika.PlainCredentials(
                    self.rabbit_mq_config.username,
                    self.rabbit_mq_config.password)))
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange=self.rabbit_mq_config.exchange,
            type=self.rabbit_mq_config.exchange_type,
            durable=False)


class FakeHalondConsumer(FakeHalondRMQ):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond Rabbit-MQ consumer.
    """

    def __init__(self, config_file_path, callback_function):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """
        super(FakeHalondConsumer, self).__init__(config_file_path)
        self._channel.queue_declare(
            queue=self.rabbit_mq_config.exchange_queue,
            exclusive=True)
        self._channel.queue_bind(
            exchange=self.rabbit_mq_config.exchange,
            queue=self.rabbit_mq_config.exchange_queue)
        self._channel.basic_consume(
            lambda ch, method, properties, body:
            callback_function(body),
            queue=self.rabbit_mq_config.exchange_queue,
            no_ack=True
        )

    def start_consuming(self):
        """
        Start consuming the queue messages.
        """
        self._channel.start_consuming()


class FakeHalondPublisher(FakeHalondRMQ):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond Rabbit-MQ publisher.
    """

    def __init__(self, config_file_path):
        """
        Initialize the object from a configuration file.

        @param config_file_path: Absolute path to configuration JSON file.
        @type config_file_path: str
        """
        super(FakeHalondPublisher, self).__init__(config_file_path)

    def publish_message(self, message):
        """
        Publish the message to Halond Rabbit-MQ queue.

        @param message: message to be published to queue.
        @type message: str
        """
        self._channel.basic_publish(
            exchange=self.rabbit_mq_config.exchange,
            routing_key=self.rabbit_mq_config.routing_key,
            body=json.dumps(message))


class HalonRquestHandler(object):
    # pylint: disable=too-few-public-methods

    """
    Class to define the Halond message request handler.
    """

    @staticmethod
    def process_request(
            body,
            channel=None,
            method=None,
            properties=None,
            fake_halond_publisher=None):
        """
        Process the message request received from the queue.
        """
        pass


class FakeHalondOutputDirectory(object):
    # pylint: disable=too-few-public-methods

    """ Manages the output directory where fake_halond stores the messages
    (that would otherwise be processed by the real halond.)
    """

    def __init__(self, directory, _cleanup_funcs):
        # pylint: disable=unused-argument
        """ Creates the specified directory and prepares it for storage of fake
        halond messages.

        @param directory          The name of the directory to be created, eg
                                  '/tmp/fake_halond'.  The directory must not
                                  previously exist.  The directory (and it's
                                  contents) will be deleted when the program
                                  exits.
        """
        if os.path.exists(directory):
            raise RuntimeError(
                "The path {} already exists.  (Refusing to continue.)"
                .format(directory)
            )
        self._directory = directory
        self._count = 0
        _cleanup_funcs += [self._remove_directory]
        os.mkdir(self._directory)

    def write_message_to_directory(self, message):
        """ Write the specified output message to the output directory.

        The filename will be <number>.json (even if the message isn't json)
        where <number> is 1 for the first message, 2 for the second message,
        etc.

        This is expected to be used as a callback to rabbitmq.

        @param message:           The output message.  It will be written to
                                  the file without any further processing.
        """
        self._count += 1
        filename = os.path.join(self._directory, "{}.json".format(self._count))
        with open(filename, 'w') as output:
            output.write(message)

    def _remove_directory(self):
        """ Remove the registered directory.

        Expected to occur at program exit.
        """
        shutil.rmtree(self._directory, ignore_errors=True)


def parse_arguments():
    """ Parse command line arguments. """
    parser = argparse.ArgumentParser(
        description='A fake halond that listens to rabbitmq for messages and '
        'then dumps them to the specified directory.'
    )
    parser.add_argument(
        '-d', '--directory',
        default='/tmp/fake_halond',
        help='Output directory.  Will be created upon startup, and removed '
        'upon shutdown.  Defaults to /tmp/fake_halond.'
    )
    parser.add_argument(
        '-p', '--pidfile',
        default='/var/run/fake_halond.pid',
        help='pidfile location.  Defaults to /var/run/fake_halond.pid'
    )
    parser.add_argument(
        '-H', '--host',
        default='localhost',
        help='Rabbitmq host to connect to.  (Defaults to "localhost" which is '
        'almost certainly what you want.)'
    )
    parser.add_argument(
        '-e', '--exchange',
        default='sspl_hl_cmd',
        help='Rabbitmq exchange.  (Defaults to "sspl_hl_cmd" which is almost '
        'certainly what you want.)'
    )
    parser.add_argument(
        '-q', '--queue',
        default='sspl_hl_cmd',
        help='Rabbitmq queue.  (Defaults to "sspl_hl_cmd" which is almost '
        'certainly what you want.)'
    )
    return parser.parse_args()


def rabbitmq_connect(host, exchange, queue, fake_output_dir):
    """ Connect to rabbitmq and setup callbacks.

    Note that we don't start consuming as part of this.  To do so, call
    start_consuming() on the returned objectect.

    @param host:                  The rabbitmq host to connect to, eg
                                  'localhost'.
    @param exchange:              The rabbitmq exchange to connect to (on the
                                  specified host.)  This will be created if it
                                  doesn't already exist.
    @param queue:                 The rabbitmq queue to connect to (from the
                                  given exchange).  This will be created if it
                                  doesn't already exist.
    @type fake_output_dir         FakeHalondOutputDirectory
    @param fake_output_dir        Object that managers the directory where the
                                  output messages will be placed.
    @return:                      A rabbitmq channel.
    """
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=host,
            virtual_host="SSPL",
            credentials=pika.PlainCredentials('sspluser', 'sspl4ever')
        )
    )
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange, type='topic', durable=False)
    channel.queue_declare(queue=queue, exclusive=True)
    channel.queue_bind(exchange=exchange, queue=queue)
    channel.basic_consume(
        lambda ch, method, properties, body:
        fake_output_dir.write_message_to_directory(body),
        queue=queue,
        no_ack=True
    )
    return channel


def create_pidfile(pidfile, _cleanup_funcs):  # pylint: disable=unused-argument
    """ Writes the pid for the process into the indicated file.

    The pidfile will be automatically removed upon program exit (unless the
    process is kill -9'd or similar, of course.)

    @type pidfile:                string
    @param pidfile:               The path to the file.  The pid will be
                                  written to this file.
    @raise RuntimeError:          Raised if the file pointed to by pidfile
                                  already exists.
    """
    if os.path.exists(pidfile):
        raise RuntimeError(
            "Error: Pidfile '{pidfile}' already exists."
            .format(pidfile=pidfile)
        )

    def _remove_pid_file():
        """ Remove the pid file, ignoring 'no such file...' errors. """
        try:
            os.unlink(pidfile)
        except OSError as err:
            if err.errno != 2:
                raise

    _cleanup_funcs += [_remove_pid_file]
    with open(pidfile, 'w') as output:
        output.write('{}'.format(os.getpid()))


def main():
    """ main """
    _cleanup_funcs = []
    signal.signal(signal.SIGINT, lambda x, y: _cleanup(_cleanup_funcs))
    signal.signal(signal.SIGTERM, lambda x, y: _cleanup(_cleanup_funcs))
    args = parse_arguments()
    create_pidfile(args.pidfile, _cleanup_funcs)
    fake_output_dir = FakeHalondOutputDirectory(args.directory, _cleanup_funcs)
    # channel = rabbitmq_connect(
    #    args.host, args.exchange, args.queue, fake_output_dir
    # )
    # channel.start_consuming()

    # halond_request_handler = HalonRquestHandler()
    consumer = FakeHalondConsumer(
        None,
        fake_output_dir.write_message_to_directory)
    consumer.start_consuming()

    # never reached
    assert False


if __name__ == '__main__':
    main()
