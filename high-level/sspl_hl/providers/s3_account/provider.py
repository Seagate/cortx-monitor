# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# _author_ = "Vikram chhajer"

from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.s3admin.s3_utils import get_client
from sspl_hl.utils.s3admin.account_handler import AccountUtility
from twisted.internet.threads import deferToThread
from sspl_hl.utils.message_utils import S3CommandResponse


class S3AccountProvider(BaseCastorProvider):
    def __init__(self, name, description):
        super(S3AccountProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command', 'action', 'name', 'email']
        self.valid_commands = ['account']
        self.valid_subcommands = ['create', 'list']
        self.mandatory_args = ['command', 'action']
        self.no_of_arguments = 4

    def handleRequest(self, request):
        try:
            self.render_query(request)
        except Exception as ex:
            print str(ex)

    def render_query(self, request):
        """
        S3 Account request handler.
        """
        if not super(S3AccountProvider, self).render_query(request):
            return
        self.process_s3auth_request(request)

    def process_s3auth_request(self, request):
        """
        Process the request bundle request based on the command
        """
        action = request.selection_args.get('action', None)
        if action == 'create':
            self.create_account_command(request)
        elif action == 'list':
            self.execute_list_command(request)

    def create_account_command(self, request):
        client = get_client(None, None, None, "iam")
        name = request.selection_args.get('name', None)
        email = request.selection_args.get('email', None)
        account_handler = AccountUtility(client, name, email)
        deferred = deferToThread(account_handler.create())
        deferred.addCallback(self._handle_create_success, request)
        deferred.addErrback(self._handle_failure)

    def execute_list_command(self, request):
        client = get_client(None, None, None, "iam")
        account_handler = AccountUtility(client)
        deferred = deferToThread(account_handler.list())
        deferred.addCallback(self._handle_list_success, request)
        deferred.addErrback(self._handle_failure)

    def _handle_create_success(self, account_info, request):
        response = S3CommandResponse()
        msg = response.get_response_message('create', account_info)
        request.reply(msg)

    def _handle_failure(self, failure):
        self.log_info("Failed " + str(failure))

    def _handle_list_success(self, accounts_info, request):
        response = S3CommandResponse()
        msg = response.get_response_message('list', accounts_info)
        request.reply(msg)
