"""
PLEX data provider.
"""
# Third Party
from twisted.internet import reactor

# PLEX
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.message_utils import NodeStatusRequest, NodeServiceRequest


class NodeProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """ Used to set state of nodes on the cluster. """

    def __init__(self, name, description):
        super(NodeProvider, self).__init__(name, description)
        self.valid_arg_keys = ['target', 'command', 'debug']
        self.valid_commands = ['start',
                               'stop',
                               'enable',
                               'disable',
                               'list',
                               'status']
        self.no_of_arguments = 3

    @staticmethod
    def _generate_node_request_msg(target, command):
        """ Generate a node request message.

        @param target:            Name of the node, eg 'node.XJY548'.
        @param command:           Operation.  Must be one of 'start', 'stop',
                                  'restart', 'enable', 'disable', 'status'.
        @param now:               The current time.  (iso formatted).
        @return:                  json node request message.
        @rtype:                   json
        """
        message = None
        if command == 'status':
            message = NodeStatusRequest().get_request_message("node", target)
        elif command == 'list':
            message = NodeStatusRequest().get_request_message("node", ".*")
        else:
            message = NodeServiceRequest().get_request_message(command, target)
        return message

    def _query(self, selection_args, responder):
        """ Sets state of node on the cluster.

        This generates a json message and places it into rabbitmq where it will
        be processed by halond and eventually sent out to the various nodes in
        the cluster and processed by sspl-ll.

        @param selection_args:    A dictionary that must contain 'target'
                                  and 'command' the command should be one
                                  of 'start', 'stop','restart' and 'status'
                                  and nodes value could be a regex indicating
                                  which nodes to operate on, eg
                                  'mynode0[0-2]'
        """
        result = super(NodeProvider, self)._query(selection_args, responder)
        if result:
            reactor.callFromThread(responder.reply_exception, result)
            return

        message = self._generate_node_request_msg(
            target=selection_args['target'],
            command=selection_args['command'],
            )

        self._publish_message(message)

        response = None
        if selection_args['command'] == 'status' \
                or selection_args['command'] == 'list':
            response = message
        elif selection_args['debug'] == 'True':
            response = message
        else:
            reactor.callFromThread(responder.reply_no_match)
        reactor.callFromThread(responder.reply, data=[response])


# pylint: disable=invalid-name
provider = NodeProvider("node", "Node Management Provider")
# pylint: enable=invalid-name
