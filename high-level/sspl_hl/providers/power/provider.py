"""
PLEX data provider.
"""
# Third party
from twisted.internet import reactor
# Local
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.providers.node.provider import NodeProvider


class PowerProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
        Handler for all power based commands
    """

    def __init__(self, name, description):
        super(PowerProvider, self).__init__(name, description)
        self.valid_arg_keys = ['target', 'command', 'debug']
        self.no_of_arguments = 3
        self.valid_commands = ['on', 'off', 'status']
        self._internal_cmds = {'on': 'start',
                               'off': 'stop'}

    def _query(self, selection_args, responder):
        """ Sets state of power on the cluster.

        This generates a json message and places it into rabbitmq where it will
        be processed by halond and eventually sent out to the various nodes in
        the cluster and processed by sspl_hl.

        @param selection_args:    A dictionary that must contain 'target'
                                  and 'command' the command should be one
                                  of ''on', 'off' and 'status'
                                  and nodes value could be a regex indicating
                                  which nodes to operate on, eg
                                  'mynode0[0-2]'
        """

        result = super(PowerProvider, self)._validate_params(selection_args)
        if result:
            reactor.callFromThread(responder.reply_exception, result)
            return

        selection_args['command'] = self._internal_cmds.get(
            selection_args['command'], selection_args['command'])

        node_provider = NodeProvider('node', '')
        # pylint: disable=protected-access
        node_provider._on_create()
        # pylint: disable=protected-access
        node_provider._query(
            selection_args=selection_args,
            responder=responder
            )

# pylint: disable=invalid-name
provider = PowerProvider("power", "Provider for power command")
# pylint: enable=invalid-name
