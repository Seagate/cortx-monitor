"""
Support bundle provider implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# _author_ = "Bhupesh Pant"

from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.message_utils import SupportBundleResponse
from sspl_hl.utils.support_bundle.support_bundle_handler import \
    SupportBundleHandler
import sspl_hl.utils.common as utils
from sspl_hl.utils.support_bundle import bundle_utils
from twisted.internet.threads import deferToThread


class SupportBundleProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """Support Bundle data provider"""

    def __init__(self, name, description):
        super(SupportBundleProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command']
        self.valid_commands = ['create', 'list']
        self.no_of_arguments = 1

    def render_query(self, request):
        """
        Support bundle request handler.
        """
        if not super(SupportBundleProvider, self).render_query(request):
            return
        self.process_support_bundle_request(request)

    def process_support_bundle_request(self, request):
        """
        Process the request bundle request based on the command
        """
        command = request.selection_args.get('command', None)
        if command == 'list':
            deferred_list = deferToThread(
                bundle_utils.list_bundle_files
            )
            deferred_list.addCallback(
                SupportBundleProvider.handle_success_list_bundles,
                request)
            deferred_list.addErrback(
                self.handle_failure_list_bundles,
                request)
        elif command == 'create':
            bundling_handler = SupportBundleHandler()
            bundle_name = utils.get_curr_datetime_str()
            deferred_create = bundling_handler.collect(bundle_name)
            deferred_create.addCallback(
                self.handle_success_create_bundle,
                request)
            deferred_create.addErrback(
                self.handle_failure_create_bundle,
                request)
        else:
            err_msg = 'Failure. Details: command {} is not supported'.\
                format(command)
            self.log_warning(err_msg)
            request.responder.reply_exception(err_msg)

    def handle_success_create_bundle(self, bundle_name, request):
        """
        Create bundle success handler
        """
        response = SupportBundleResponse()
        msg = response.get_response_message('create', bundle_name)
        self.log_info('Bundling has been triggered: Bundle_id: {}'.
                      format(bundle_name))
        request.reply(msg)

    def handle_failure_create_bundle(self, error, request):
        """
        Create bundle failure handler
        """
        err_msg = 'Error Occurred during bundle create. Details: {}'.\
            format(error)
        self.log_warning(err_msg)
        request.responder.reply_exception(err_msg)

    @staticmethod
    def handle_success_list_bundles(bundles_list, request):
        """
        Success handler for list command
        """
        response = SupportBundleResponse()
        msg = response.get_response_message('list', bundles_list)
        request.reply(msg)

    def handle_failure_list_bundles(self, error, request):
        """
        Failure handler for list command
        """
        err_msg = 'Error Occurred during bundle list. Details: {}'.\
            format(error)
        self.log_warning(err_msg)
        request.responder.reply_exception(err_msg)

# pylint: disable=invalid-name
provider = SupportBundleProvider('bundle',
                                 "Provider for bundle commands")
