"""
PLEX data provider for Halon resource graph for ha.
"""
import socket
from twisted.internet import reactor
# Third party
# Local
from sspl_hl.utils.base_castor_provider import BaseCastorProvider


class HaProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods

    """ Used to set state of ha on the cluster. """
    RG_COMMAND = "graph\r\n"
    RG_QUIT_CMD = "quit\r\n"
    READ_BYTE_SIZE = 4096

    def __init__(self, name, description):
        super(HaProvider, self).__init__(name, description)
        self.valid_commands = ['info', 'debug']
        self.valid_subcommands = ['show', 'status']
        self.valid_arg_keys = ['command', 'subcommand']
        self.no_of_arguments = 2
        self._frontier_node_ip = '127.0.0.1'
        self._frontier_port = 9008
        self._conn = None

    def _connect_frontier_service(self):
        """Connects to frontier service
        """
        self._conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._conn.connect((self._frontier_node_ip, self._frontier_port))

    def _receive_data(self):
        """ Receive Data from frontier service
        """
        self._conn.sendall(self.RG_COMMAND)
        self._conn.sendall(self.RG_QUIT_CMD)
        resource_graph = ""
        while 1:
            response = self._conn.recv(self.READ_BYTE_SIZE)
            if not len(response) > 0:
                break
            resource_graph += response
        self._conn.close()
        return resource_graph

    def _query(self, selection_args, responder):
        """ Get the resource graph ha on the cluster.

        @param selection_args:    A dictionary that must contain the key
                                  'resourceGraphType' and can optionally
                                  include a 'command'
        """
        result = super(HaProvider, self)._query(selection_args, responder)
        if result:
            reactor.callFromThread(responder.reply_exception, result)
            return
        try:
            halon_response = self.get_ha_resource_graph()
            reactor.callFromThread(responder.reply, data=[halon_response])
        # pylint: disable=broad-except
        except Exception as err:
            reactor.callFromThread(responder.reply_exception, "Error: \
Unable to get resource graph information:{}".format(err))

    def get_ha_resource_graph(self):
        """
        Get response from frontier service
        """
        self._connect_frontier_service()
        data = self._receive_data()
        self._conn.close()
        return data

# pylint: disable=invalid-name
provider = HaProvider("Ha", "Ha Management Provider")
# pylint: enable=invalid-name
