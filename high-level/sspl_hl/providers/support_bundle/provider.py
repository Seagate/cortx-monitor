"""
PLEX data provider.
"""
# Third party
from twisted.internet import reactor
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.common_utils import (list_available_support_bundle,
                                        create_support_bundle)


class SupportBundleProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """Data Provider"""

    def __init__(self, name, description):
        super(SupportBundleProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command']
        self.valid_commands = ['create', 'list']
        self.no_of_arguments = 1

    def _query(self, selection_args, responder):
        """ Get the support bundle details.

        @param selection_args:    includes a 'command'
        """
        result = super(SupportBundleProvider, self)._query(
            selection_args,
            responder)
        if result:
            reactor.callFromThread(responder.reply_exception, result)
            return

        response = SupportBundleProvider._process_support_bundle_request(
            selection_args['command']
            )

        reactor.callFromThread(responder.reply, data=[response])

    @classmethod
    def _process_support_bundle_request(cls, command):
        """ Process the request bundle request
        based on the command
        """

        if command == 'list':
            response = list_available_support_bundle()
        elif command == 'create':
            response = create_support_bundle()
        else:
            response = 'command %s not supported' % command
        return response

SupportBundleProvider('support_bundle',
                      "Provider for command support_bundle")
