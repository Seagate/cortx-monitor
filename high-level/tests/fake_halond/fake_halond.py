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

"""
A fake halond that listens to rabbitmq for messages and then just dumps them
out to a directory in the order in which they're received.

Usage::
    ./fake_halond.py [-d /tmp/fake_halond]

The files in the directory will be named numerically.  ie the first message
will be named 1.json, the second 2.json, the 10th 10.json.  The directory (and
all files within it) will be deleted when the process exits.
"""

# Standard
import os.path
import shutil
import argparse
import signal
import sys

# Local
from sspl_hl.utils.rabbit_mq_utils import (HalondConsumer,
                                           HalonRequestHandler,
                                           HalondPublisher)


def _cleanup(cleanup_funcs):
    """ Signal handler to perform cleanup and exit. """
    for func in cleanup_funcs:
        func()
    sys.exit(1)


class FakeHalondOutputDirectory(object):
    # pylint: disable=too-few-public-methods

    """ Manages the output directory where fake_halond stores the messages
    (that would otherwise be processed by the real halond.)
    """

    def __init__(self, directory, _cleanup_funcs, publisher):
        # pylint: disable=unused-argument
        """ Creates the specified directory and prepares it for storage of fake
        halond messages.

        @param directory:         The name of the directory to be created, eg
                                  '/tmp/fake_halond'.  The directory must not
                                  previously exist.  The directory (and it's
                                  contents) will be deleted when the program
                                  exits.
        @param publisher:         Rabbit MQ publisher.
        """
        if os.path.exists(directory):
            raise RuntimeError(
                "The path {} already exists.  (Refusing to continue.)"
                .format(directory)
            )
        self._directory = directory
        self._count = 0
        self.publisher = publisher
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
            response = HalonRequestHandler.process_request(message)
            if response:
                self.publisher.publish_message(response)

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
        '-c', '--cmdconfig',
        help='Rabbitmq command request config file path'
        'config file will have rabbit mq connection parameters)'
    )
    parser.add_argument(
        '-r', '--respconfig',
        help='Rabbitmq message response config file path'
        'config file will have rabbit mq connection parameters)'
    )
    return parser.parse_args()


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

    publisher = HalondPublisher(args.respconfig)
    fake_output_dir = FakeHalondOutputDirectory(
        args.directory,
        _cleanup_funcs,
        publisher)
    consumer = HalondConsumer(
        args.cmdconfig,
        fake_output_dir.write_message_to_directory)
    consumer.start_consuming()

    # never reached
    assert False


if __name__ == '__main__':
    main()
