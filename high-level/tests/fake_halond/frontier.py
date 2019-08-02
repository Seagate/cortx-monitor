#!/usr/bin/python3.6
"""Module that mocks Frontier service. It accepts an incoming
   connections and checks for a <COMMAND_TO_CHECK> in a received data.
   If it finds then it sends a content of
"""
# Standard imports
import argparse
import logging
import os
import socket
import signal
import sys


class FrontierService(object):

    """
    Class to implement Mock Frontier service behaviour
    """
    HOST = '0.0.0.0'
    PORT = 9008
    SIZE = 1024  # Size of data to be received at a time
    BACKLOG = 5  # No of requests to hold in queue
    COMMAND_TO_CHECK = "GRAPH"
    DEFAULT_PID_FILE = "/tmp/frontier.pid"
    RESPONSE_FILE = "./tests/fake_halond/frontier_response.txt"

    def __init__(self, pid_file=None):
        self._log = self._setup_logging()
        self._pid_file = pid_file or FrontierService.DEFAULT_PID_FILE
        self.log_info("Starting Frontier service...")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )  # To reuse the port
        self._sock.bind((FrontierService.HOST, FrontierService.PORT))
        self._sock.listen(FrontierService.BACKLOG)
        self.log_info(
            'Listening on {host}:{port}'
            .format(host=FrontierService.HOST, port=FrontierService.PORT)
        )

    def log_info(self, log_text):
        """
        Logs a text as information
        @param log_text: Information to be logged
        @type log_text: str
        """
        self._log.info(log_text)

    def log_error(self, log_text):
        """
        Logs a text as error
        @param log_text: Error to be logged
        @type log_text: str
        """
        self._log.error(log_text)

    def close_socket(self):
        """
        Closes socket
        """
        self._sock.close()
        self._sock = None

    def create_pid_file(self):
        """ Wries current process id to <pid_file>
            @raise RuntimeError: Raised if the file pointed to by pidfile
                                already exists.
        """
        if os.path.exists(self._pid_file):
            raise RuntimeError(
                "Error: Pid file '{pidfile}' already exists."
                .format(pidfile=self._pid_file)
            )

        with open(self._pid_file, 'w') as output:
            output.write('{}'.format(os.getpid()))
        self.log_info("Written PID to {pidfile}".
                      format(pidfile=self._pid_file))

    def remove_pid_file(self):
        """Removes existing <pid_file> file
        """
        if os.path.exists(self._pid_file):
            os.unlink(self._pid_file)

    @staticmethod
    def _setup_logging():
        """Setup logging
        """
        log = logging.getLogger("Frontier")
        log.setLevel(logging.INFO)
        sth = logging.StreamHandler()
        sth.setLevel(logging.INFO)
        log.addHandler(sth)
        return log

    @staticmethod
    def send_data(data_to_send, client_socket):
        """ Sends <data_to_send> to <client_socket>

            @param data_to_send: Data to be sent to <client_socket>
            @type data_to_send:str

            @param client_socket: Socket related with client
            @type client_socket: Instance of socket
        """
        client_socket.send(data_to_send)

    @staticmethod
    def get_data_from_file(file_path):
        """
        Returns contents of <file_path>
        @param file_path: Absolute or relative Path of
                         file to read
        @type file_path: str
        @return: Content of <file_path> if reads successful,
                 None otherwise
        @rtype: str
        """
        frontier_response = None
        with open(file_path) as response_file:
            frontier_response = response_file.read()
        return frontier_response

    def start_service(self):
        """Starts a listening and ready to accept
           requests
        """
        data_to_send = FrontierService.get_data_from_file(
            FrontierService.RESPONSE_FILE
        )
        while True:
            client, address = self._sock.accept()
            self.log_info("Got request from {address}".format(address=address))
            # pylint: disable=no-member
            received_data = client.recv(FrontierService.SIZE)

            if received_data:
                if FrontierService.COMMAND_TO_CHECK.lower(
                ) in received_data.lower():
                    found_msg = "Found %s in received data from %s" % (
                        FrontierService.COMMAND_TO_CHECK, address)
                    self.log_info(found_msg)
                    self.send_data(
                        data_to_send=data_to_send,
                        client_socket=client
                    )
                    self.log_info("Data sent")
                elif "exit" in received_data.lower():
                    self.log_info("Received exit command...")
                    self.remove_pid_file()
                    break
            client.close()

    @staticmethod
    def parse_arguments():
        """ Parse command line arguments. """
        parser = argparse.ArgumentParser(
            description='It receives a command GRAPH and returns some data')

        parser.add_argument(
            '-p', '--pidfile',
            default=FrontierService.DEFAULT_PID_FILE,
            help='pid file location. Defaults to %s'
            % FrontierService.DEFAULT_PID_FILE
        )
        return parser.parse_args()

    def sigterm_handler(self):
        """
        Handles termination signal
        Note: Arguments signal_no and
              stack_frame omitted due to
              pylint issue unused-argument
        """
        self._sock.close()
        self._sock = None
        self.remove_pid_file()
        sys.exit(0)


def main():
    """Main function
    """
    args = FrontierService.parse_arguments()
    frontier_service = FrontierService(pid_file=args.pidfile)
    signal.signal(signal.SIGTERM, frontier_service.sigterm_handler)

    try:
        frontier_service.create_pid_file()
        frontier_service.start_service()
    except IOError as io_error:
        frontier_service.log_error(str(io_error))
    except socket.error as socket_error:
        frontier_service.log_error(str(socket_error))
    except KeyboardInterrupt as kb_int:
        frontier_service.log_error(str(kb_int))
    except Exception as exception:  # pylint: disable=broad-except
        frontier_service.log_error(str(exception))
    finally:
        frontier_service.log_info("Closing socket")
        frontier_service.close_socket()
        frontier_service.log_info("Removing pid file")
        frontier_service.remove_pid_file()
        frontier_service.log_info("Exiting...")


if __name__ == "__main__":
    main()
