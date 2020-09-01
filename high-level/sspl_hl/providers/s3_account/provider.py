# Copyright (c) 2017 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.



from twisted.internet.threads import deferToThread

from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.s3admin.s3_utils import get_client
from sspl_hl.utils.s3admin.account_handler import AccountUtility
from sspl_hl.utils.message_utils import S3CommandResponse
from sspl_hl.utils.strings import Strings


class S3AccountProvider(BaseCastorProvider):
    def __init__(self, name, description):
        """
        S3AccountProvider Constructor
        """
        super(S3AccountProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command', 'action', 'name', 'email',
                               'access_key', 'secret_key', 'force']
        self.valid_commands = ['account']
        self.valid_subcommands = [Strings.CREATE, Strings.LIST, Strings.REMOVE]
        self.mandatory_args = ['command', 'action']
        self.no_of_arguments = 7
        self.client = None

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
        self.process_s3admin_request(request)

    def process_s3admin_request(self, request):
        """
        Process the request bundle request based on the command.
        """
        self.client, response = get_client(service=Strings.IAM_SERVICE)
        if self.client is None:
            request.reply(S3CommandResponse().get_response_message(response))
        else:
            self.execute_command(request)

    def execute_command(self, request):
        """
        Execute operation based on request.
        """
        action = request.selection_args.get('action', None)
        account_handler = AccountUtility(self.client, request.selection_args)
        if action == Strings.CREATE:
            deferred = deferToThread(account_handler.create())
        elif action == Strings.LIST:
            deferred = deferToThread(account_handler.list())
        elif action == Strings.REMOVE:
            deferred = deferToThread(account_handler.remove())

        deferred.addCallback(self._handle_success, request)
        deferred.addErrback(self._handle_failure)

    def _handle_success(self, account_info, request):
        """Handle operation response received from S3 server.

        This will be called when operation was successful.
        """
        response = S3CommandResponse()
        msg = response.get_response_message(account_info)
        request.reply(msg)

    def _handle_failure(self, failure):
        """Handle failure case for  all operations.

        This will be called when operation was failed due to unknwon reasons.
        """
        self.log_info("Failed " + str(failure))
