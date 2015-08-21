"""
PLEX data provider.
"""
# Third Party
from twisted.internet import reactor

# PLEX
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.message_utils import FRUStatusRequest, FRUServiceRequest


class FRUProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """ Used to set state of frus on the cluster. """

    def __init__(self, name, description):
        super(FRUProvider, self).__init__(name, description)
        self.valid_arg_keys = ['target', 'command', 'debug']
        self.no_of_arguments = 3

    @staticmethod
    def _generate_fru_request_msg(fru_target, fru_command):
        """ Generate a fru request message.

        @param fru_target:        Name of the node, eg 'node.XJY548'.
        @param fru_command:       Operation.  Must be one of 'status', 'list'
        @param now:               The current time.  (iso formatted).
        @return:                  json fru request message.
        @rtype:                   json
        """
        message = None
        if fru_command == 'status':
            message = FRUStatusRequest().get_request_message("fru", fru_target)
        else:
            message = FRUServiceRequest().get_request_message(
                fru_command,
                fru_target
            )
        return message

    def _query(self, selection_args, responder):
        """ Sets state of fru on the cluster.

        This generates a json message and places it into rabbitmq where it will
        be processed by halond and eventually sent out to the various frus in
        the cluster and processed by sspl-ll.

        @param selection_args:    A dictionary that must contain 'target'
                                  and 'command'. The command should be one
                                  of 'list' and 'status' and frus value could
                                  be a regex indicating which nodes to operate
                                  on, eg 'mynode0[0-2]'
        """
        result = super(FRUProvider, self)._query(selection_args, responder)
        if result:
            reactor.callFromThread(responder.reply_exception, result)
            return

        fru_message = self._generate_fru_request_msg(
            fru_target=selection_args['target'],
            fru_command=selection_args['command'],
            )

        self._publish_message(fru_message)

        response = None
        if selection_args['command'] == 'status':
            response = fru_message
        elif selection_args['command'] == 'list':
            response = fru_message
        elif selection_args['debug'] == 'True':
            response = fru_message
        else:
            reactor.callFromThread(responder.reply_no_match)
        reactor.callFromThread(responder.reply, data=[response])


# pylint: disable=invalid-name
provider = FRUProvider("fru", "FRU Management Provider")
# pylint: enable=invalid-name
