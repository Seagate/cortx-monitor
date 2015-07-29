"""
PLEX data provider for Halon resource graph for ha.
"""
# Third party
from twisted.internet import reactor
import urllib
# PLEX
# Local

from plex.util.concurrent.single_thread_executor import SingleThreadExecutor
from sspl_hl.utils.message_utils import (HaResourceGraphResponse,
                                         ERR_INVALID_RQ,
                                         ERR_INVALID_CMD,
                                         ERR_MISSING_CMD)

from sspl_hl.utils.base_castor_provider import BaseCastorProvider


class HaProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods

    """ Used to set state of ha on the cluster. """

    def __init__(self, name, description):
        super(HaProvider, self).__init__(name, description)
        self._single_thread_executor = SingleThreadExecutor()
        self._frontier_node_ip = None
        self._frontier_port = None
        self.frontier_service_url = None

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
            self._start_froniter_service()

    @staticmethod
    def _is_frontier_service_running():
        """
        Check if frontier service is running on satellite or Halon node
        """
        return True

    @staticmethod
    def _start_froniter_service():
        """
        Start the frontier service on given satellite or Halon node
        """
        pass

    @staticmethod
    def _validate_params(selection_args, responder):
        """ Ensure query() parameters are ok. """
        valid_commands = [
            'show', 'status'
        ]
        valid_levels = ['info', 'debug']
        if 'level' not in selection_args:
            reactor.callFromThread(responder.reply_exception(
                "Error: Invalid request: Missing level"
            ))
            return False
        elif 'command' not in selection_args:
            reactor.callFromThread(responder.reply_exception(ERR_MISSING_CMD))
            return False
        elif selection_args['command'] not in valid_commands:
            reactor.callFromThread(responder.reply_exception(
                ERR_INVALID_CMD.format(
                    selection_args['command']
                )
            ))
            return False
        elif selection_args['level'] not in valid_levels:
            reactor.callFromThread(responder.reply_exception(
                ERR_INVALID_RQ.format(
                    selection_args['level']
                )
            ))
            return False
        elif len(selection_args) > 2:
            del selection_args['level']
            del selection_args['command']
            reactor.callFromThread(
                responder.reply_exception(
                    ERR_INVALID_RQ.format(
                        extra=selection_args.keys()[0])))
            return False

        return True

    def _query(self, selection_args, responder):
        """ Get the resource graph ha on the cluster.

        @param selection_args:    A dictionary that must contain the key
                                  'resourceGraphType' and can optionally
                                  include a 'command'
        """
        if not self._validate_params(selection_args, responder):
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

        """
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

# pylint: disable=invalid-name
provider = HaProvider("ha", "Ha Management HaProvider")
# pylint: enable=invalid-name
