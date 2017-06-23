"""
PLEX data provider.
"""
# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# __author__ = 'Bhupesh Pant'

# Third party
from twisted.internet.threads import deferToThread
from zope.interface import implements
from twisted.plugin import IPlugin
# PLEX
from plex.common.interfaces.idata_provider import IDataProvider
# Local
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.message_utils import UserMgmtCommandResponse
from sspl_hl.utils.user_mgmt.user import User
from sspl_hl.utils.user_mgmt.user_mgmt import UserMgmt


class UserMgmtProvider(BaseCastorProvider):
    """Data Provider"""
    implements(IPlugin, IDataProvider)

    def __init__(self, title, description):
        """"""
        # "Selection Args:  {'pwd': 'bhanu123', 'command':
        # 'create', 'user': 'bhanu', 'components': 'ras,halon'}
        super(UserMgmtProvider, self).__init__(title, description)
        self.valid_arg_keys = ["command", "user", "pwd", "components"]
        self.no_of_arguments = 4
        self.valid_commands = ["create", "remove"]
        self.valid_subcommands = []
        self.mandatory_args = ["command", "user"]

    def render_query(self, request):
        """Handling all the user mgmt request queries."""
        # Validate request params
        self.log_debug('Request Received: Type: {}'.format(
            request.selection_args.get('command', None))
        )
        if not super(UserMgmtProvider, self).render_query(request):
            return
        self.process_request(request)

    def process_request(self, request):
        """Handle the user_management request"""
        command = request.selection_args.get('command', None)
        user = self.get_user_obj(request.selection_args)
        user_mgmt = UserMgmt()
        if command == 'create':
            self.log_debug('User creation with params : {}'.format(user))
            deferred_list = deferToThread(user_mgmt.create_user, user)
            deferred_list.addCallback(
                self.handle_success_operation,
                user, request)
            deferred_list.addErrback(
                self.handle_failure_operation,
                user, request)
        elif command == 'remove':
            self.log_debug('User deletion with params: {}'.format(user))
            deferred_list = deferToThread(user_mgmt.remove_user, user)
            deferred_list.addCallback(
                self.handle_success_operation,
                user, request)
            deferred_list.addErrback(
                self.handle_failure_operation,
                user, request)

    def get_user_obj(self, params):
        """Populate and return user object"""
        return User(username=params.get('user'),
                    pwd=params.get('pwd'),
                    authorizations=params and
                    params.get('components').split(','))

    def handle_configure_user(self, user):
        """Handles configuring the new User and err checking"""
        user_mgmt = UserMgmt()
        self.log_debug('[{}] will be configured!'.format(user.username))
        result = user_mgmt.configure_user(user)
        if result.get('ret_code') == 0:
            self.log_info('User: [{}] is successfully Configured for: [{}]'.
                          format(user.username, user.authorizations))
            return result
        else:
            self.log_warning('User: [{}] Configuration Failed. Details: [{}]'
                             .format(user.username, result.get('output')))
            # Take a fall back step by removing the new created user
            user_mgmt.remove_user(user)
            self.log_debug('User: [{}] is deleted from the system.'.format(
                user.username
            ))
            result = dict(ret_code=1,
                          output='User creation failed during configuration')
            return result

    def handle_success_operation(self, result, user, request):
        """Handle success action of create_user by responding
        back to the UI"""
        command = request.selection_args.get('command', None)
        if result.get('ret_code') == 0:
            self.log_info('User,[{}] has been {}d successfully'.
                          format(user.username, command))
            if command == 'create':
                result = self.handle_configure_user(user)

            resp = UserMgmtCommandResponse()
            message = resp.get_response_message(user, request, result)
            request.reply(message)
        else:
            self.handle_failure_operation(request, user, request)

    def handle_failure_operation(self, err, user, request):
        """Handles failed user management operations"""
        command = request.selection_args.get('command', None)
        if not isinstance(err, dict):
            err = dict(ret_code=1, output=str(err))
        self.log_warning('User,{} could not be {}d. Details: [{}]'.format(
            user.username, command, err.get('output', err)
        ))
        resp = UserMgmtCommandResponse()
        message = resp.get_response_message(user, request, err)
        request.responder.reply_exception(message)


provider = UserMgmtProvider(
    "Provider handling User Management commands",
    "This will contain all the interfaces for User Management.")
