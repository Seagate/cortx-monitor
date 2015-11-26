"""
PLEX data provider.
"""
# Third party

from twisted.internet import reactor
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.message_utils import SupportBundleResponse
from sspl_hl.utils.support_bundle.support_bundle_handler import \
    SupportBundleHandler
import sspl_hl.utils.common as utils
from sspl_hl.utils.support_bundle import bundle_utils


# """
# DEFAULT_LOG_FILES: This would contain the meta data for the files that
# needs to be bundled from various different nodes/cluster.
#
# DEFAULT_PATH: It will contain the path where tar files will be created.
# NOTE: Both these parameters will be later moved to plex configuration.
# """


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
            msg = 'Bundle command failed. Details: {}'.format(result)
            self.log_warning(msg)
            reactor.callFromThread(responder.reply_exception, result)
            return
        response = self.process_support_bundle_request(
            selection_args['command']
        )

        reactor.callFromThread(responder.reply, data=[response])

    def process_support_bundle_request(self, command):
        """ Process the request bundle request
        based on the command
        """
        response = SupportBundleResponse()
        if command == 'list':
            bundle_list = bundle_utils.list_bundle_files()
            response = response.get_response_message(command, bundle_list)
        elif command == 'create':
            bundling_handler = SupportBundleHandler()
            bundle_name = utils.get_curr_datetime_str()
            deferred = bundling_handler.collect(bundle_name)
            deferred.addCallback(self.handle_success)
            deferred.addErrback(self.handle_failure)
            response = response.get_response_message(
                command, bundle_name + '.tar')
        else:
            response = 'command %s not supported' % command
        return response

    def handle_success(self, _):
        """
        Success Handler
        """
        self.log_info('Bundling of logs Completed Successfully')

    def handle_failure(self, error):
        """
        Error Handler
        """
        self.log_info('Bundling of logs Failed. Details: {}'.format(error))

# pylint: disable=invalid-name
provider = SupportBundleProvider('bundle',
                                 "Provider for bundle commands")
