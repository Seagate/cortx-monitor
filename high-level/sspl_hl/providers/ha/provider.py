"""
PLEX data provider for Halon resource graph for ha.
"""
# Third party
from twisted.internet import reactor

# Local
from sspl_hl.utils.message_utils import HaResourceGraphResponse
from sspl_hl.utils.base_castor_provider import BaseCastorProvider


class HaProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods

    """ Used to set state of ha on the cluster. """

    def __init__(self, name, description):
        super(HaProvider, self).__init__(name, description)
        self.valid_commands = ['info', 'debug']
        self.valid_subcommands = ['show', 'status']
        self.valid_arg_keys = ['command', 'subcommand']
        self._frontier_node_ip = None
        self._frontier_port = None
        self.frontier_service_url = None
        self.no_of_arguments = 2

    def on_create(self):
        self._frontier_node_ip = '127.0.0.1'
        self._frontier_port = '9028'
        self.frontier_service_url = 'http://{}:{}'.format(
            self._frontier_node_ip,
            self._frontier_port)
        self._single_thread_executor.submit(self._on_create)

    def _on_create(self):
        """ Implement this method to initialize the HaProvider. """
        if not self._is_frontier_service_running():
            self._start_frontier_service()

    @staticmethod
    def _is_frontier_service_running():
        """
        Check if frontier service is running on satellite or Halon node
        """
        return True

    @staticmethod
    def _start_frontier_service():
        """
        Start the frontier service on given satellite or Halon node
        """
        pass

    def _query(self, selection_args, responder):
        """ Get the resource graph ha on the cluster.

        @param selection_args:    A dictionary that must contain the key
                                  'resourceGraphType' and can optionally
                                  include a 'command'
        """
        result = super(HaProvider, self)._query(selection_args, responder)
        if result:
            reactor.callFromThread(responder.reply_exception(result))
            return
        halon_response = self._get_mocked_ha_resource_graph()
        reactor.callFromThread(responder.reply(data=[halon_response]))

    @staticmethod
    def _get_mocked_ha_resource_graph():
        """
        Get the mocked Halon resource graph for ha

        @return: return mocked Halon resource graph for ha
        @rtype: dict
        """
        rg_response = HaResourceGraphResponse()
        return rg_response.get_response_message()

    def _get_ha_resource_graph(self, responder):
        """
        Get the Halon resource graph for ha from frontier service

        @return: return Halon resource graph for ha
        @rtype: dict

        try:
            rg_response = urllib.urlopen(self.frontier_service_url).read()
            # may need to do some parsing of data and conversion to dict
            return rg_response
        # pylint: disable=broad-except
        except Exception as err:
            reactor.callFromThread(
                responder.reply_exception(
                    "Error: Unable to get resource graph information:{}"
                    .format(err)))
        """

# pylint: disable=invalid-name
provider = HaProvider("ha", "Ha Management Provider")
# pylint: enable=invalid-name
