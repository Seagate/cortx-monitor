"""
PLEX data provider for Halon resource graph for ha.
"""
# Third party
from twisted.internet import reactor
import socket

# Local
from sspl_hl.utils.base_castor_provider import BaseCastorProvider


class HaProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
    Used to set state of ha on the cluster.
    """

    RG_COMMAND = "graph\r\n"
    RG_QUIT_CMD = "quit\r\n"
    READ_BYTE_SIZE = 8192

    def __init__(self, name, description):
        super(HaProvider, self).__init__(name, description)
        self.valid_commands = ['debug']
        self.valid_subcommands = ['show']
        self.valid_arg_keys = ['command', 'subcommand']
        self._frontier_node_ip = '127.0.0.1'
        self._frontier_port = 9008
        self.no_of_arguments = 2

    def _query(self, selection_args, responder):
        """ Get the resource graph ha on the cluster.

        @param selection_args:    A dictionary that must contain the key
                                  'resourceGraphType' and can optionally
                                  include a 'command'
        """
        result = super(HaProvider, self)._query(selection_args, responder)
        if result:
            reactor.callFromThread(responder.reply_exception, result)
        else:
            self._get_resource_graph(responder)

    def _get_resource_graph(self, responder):
        """
        Connect to frontier service and fetch RG.
        """
        try:
            frontier_sock = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )
            frontier_sock.connect((
                self._frontier_node_ip,
                self._frontier_port
            ))
            frontier_sock.sendall(self.RG_COMMAND)
            frontier_sock.sendall(self.RG_QUIT_CMD)
            resource_graph = ""
            while 1:
                response = frontier_sock.recv(self.READ_BYTE_SIZE)
                if not len(response) > 0:
                    break
                resource_graph += response
            reactor.callFromThread(responder.reply, data=[resource_graph])
        except socket.error as msg:
            reactor.callFromThread(responder.reply_exception, msg)
        finally:
            frontier_sock.close()

# pylint: disable=invalid-name
provider = HaProvider("ha", "Ha Management Provider")
# pylint: enable=invalid-name
