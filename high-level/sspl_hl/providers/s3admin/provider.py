"""
S3Admin provider implementation
"""

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

from sspl_hl.providers.s3_account.provider import S3AccountProvider
# from sspl_hl.providers.s3_users.provider import S3UsersProvider
# from sspl_hl.providers.s3_access_key.provider import S3AccessKeyProvider


class S3AdminProvider(BaseCastorProvider):
    """S3Admin data provider"""

    def __init__(self, name, description):
        super(S3AdminProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command', 'action', 'name', 'email',
                               'access_key', 'secret_key', 'user_access_key']
        self.valid_commands = ['account', 'user', 'access_key']
        self.valid_sub_commands = ['create', 'delete', 'modify', 'list']
        self.mandatory_args = ['command', 'action']
        self.no_of_arguments = 7
        self._child_provider = None

    def render_query(self, request):
        """
        S3 Auth request handler.
        """
        self.process_s3admin_request(request)

    def process_s3admin_request(self, request):
        """
        Process the s3 auth request based on the command
        """
        command = request.selection_args.get('command', None)
        if command == 'account':
            self.handle_account_command(request)
        elif command == 'user':
            self.handle_users_command(request)
        elif command == 'access_key':
            self.handle_access_key_command(request)
        else:
            err_msg = 'Failure. Details: command {} is not supported'. \
                format(command)
            self.log_warning(err_msg)
            request.responder.reply_exception(err_msg)

    def handle_account_command(self, request):

        self._child_provider = S3AccountProvider("account", "handling account")
        self._child_provider.handleRequest(request)

    def handle_users_command(self, request):
        pass
        # self._child_provider = S3UsersProvider("users", "handling users")
        # self._child_provider.handleRequest(request)

    def handle_access_key_command(self, request):
        pass
        # self._child_provider = S3AccessKeyProvider(
        #    "access_key", "handling access keys")
        # self._child_provider.handleRequest(request)


# pylint: disable=invalid-name
provider = S3AdminProvider('s3admin',
                           "Provider for s3admin commands")
