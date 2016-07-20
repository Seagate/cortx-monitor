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
                bundle_utils.get_bundle_info
            )
            deferred_list.addCallback(
                self.handle_success_list_bundles,
                request)
            deferred_list.addErrback(
                self.handle_failure_list_bundles,
                request)
        elif command == 'create':
            bundling_handler = SupportBundleHandler()
            bundle_name = utils.get_curr_datetime_str()
            deferred_create = bundling_handler.collect(bundle_name)
            # pylint: disable=no-member
            deferred_create.addCallback(
                self.handle_success_create_bundle,
                request,
                bundle_name
            )
            # pylint: disable=no-member
            deferred_create.addErrback(
                self.handle_failure_create_bundle,
                bundle_name
            )
            self.handle_success_create_bundle(None, request, bundle_name)
        else:
            err_msg = 'Bundle command Failure. ' \
                      'Details: command {} is not supported'. \
                format(command)
            self.log_warning(err_msg)
            request.responder.reply_exception(err_msg)

    def handle_success_create_bundle(self, result, request, bundle_name):
        """
        Create bundle success handler
        """
        bundle_name = '{}.tar'.format(bundle_name)
        if result:
            self.log_info('Bundling for Bundle_id: {} is Complete'.
                          format(bundle_name))
        else:
            response = SupportBundleResponse()
            msg = response.get_response_message('create', bundle_name)
            self.log_info('Bundling has been triggered: Bundle_id: {}'.
                          format(bundle_name))
            request.reply(msg)

    def handle_failure_create_bundle(self, error, bundle_name):
        """
        Create bundle failure handler
        """
        bundle_name = '{}.tar'.format(bundle_name)
        err_msg = 'Error Occurred during bundle create for Bundle_id: {}. ' \
                  'Details: {}'. \
            format(bundle_name, error)
        self.log_warning(err_msg)

    def handle_success_list_bundles(self, bundles_info, request):
        """
        Success handler for list command
        """
        response = SupportBundleResponse()
        msg = response.get_response_message('list', bundles_info)
        self.log_info('Bundle list response: {}'.format(msg))
        request.reply(msg)

    def handle_failure_list_bundles(self, error, request):
        """
        Failure handler for list command
        """
        err_msg = 'Error Occurred during bundle list. Details: {}'. \
            format(error)
        self.log_warning(err_msg)
        request.responder.reply_exception(err_msg)

# pylint: disable=invalid-name
provider = SupportBundleProvider('bundle',
                                 "Provider for bundle commands")
