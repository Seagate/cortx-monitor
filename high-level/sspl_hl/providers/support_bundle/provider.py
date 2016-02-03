"""
PLEX data provider.
"""
# Third party

from twisted.internet import reactor
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.bundle_utils import (list_bundle_files,
                                        bundle_files)
from sspl_hl.utils.message_utils import SupportBundleResponse

# """
# DEFAULT_LOG_FILES: This would contain the meta data for the files that
# needs to be bundled from various different nodes/cluster.
#
# DEFAULT_PATH: It will contain the path where tar files will be created.
# NOTE: Both these parameters will be later moved to plex configuration.
# """

# pylint: disable=dangerous-default-value
DEFAULT_TARGET_FILES = {'n1': ['/var/log/plex/*.log'],
                        'n2': []}
DEFAULT_PATH = '/var/lib/support_bundles'


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
        try:
            response = SupportBundleProvider._process_support_bundle_request(
                selection_args.get('command', None)
            )
            reactor.callFromThread(responder.reply, data=[response])
        except OSError as error:
            msg = '{} bundle command failed. Details: {}'.format(
                selection_args.get('command', None),
                str(error)
            )
            self.log_warning(msg)
            reactor.callFromThread(responder.reply_exception,
                                   'An Internal error has occurred, unable to '
                                   'complete command.')

    @classmethod
    def _process_support_bundle_request(cls, command):
        """ Process the request bundle request
        based on the command
        """
        response = SupportBundleResponse()
        if command == 'list':
            bundle_list = list_bundle_files(path=DEFAULT_PATH)
            response = response.get_response_message(command, bundle_list)
        elif command == 'create':
            bundle_name = bundle_files(DEFAULT_TARGET_FILES, DEFAULT_PATH)
            response = response.get_response_message(command, bundle_name)
        else:
            response = 'command %s not supported' % command
        return response

# pylint: disable=invalid-name
provider = SupportBundleProvider('support_bundle',
                                 "Provider for command support_bundle")
