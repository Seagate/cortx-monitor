from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.s3admin.user_handler import UsersUtility
from sspl_hl.utils.s3admin.s3_utils import get_client
from twisted.internet.threads import deferToThread
from sspl_hl.utils.message_utils import S3CommandResponse
from sspl_hl.utils.s3admin.s3_utils import Strings


class S3UsersProvider(BaseCastorProvider):
    def __init__(self, name, description):
        super(S3UsersProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command', 'action', 'name',
                               'email', 'path', 'access_key', 'secret_key',
                               'new_name']
        self.valid_commands = ['user']
        self.valid_subcommands = ['create', 'list', 'modify', 'remove']
        self.mandatory_args = ['command', 'action', 'access_key', 'secret_key']
        self.no_of_arguments = 8
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
        try:
            self.log_info("s3 users Render query fired. %s " %
                          request.selection_args.get('secret_key'))
            if not super(S3UsersProvider, self).render_query(request):
                self.log_info("Render query failed.")
                return
            self.process_s3admin_request(request)
        except Exception as ex:
            self.log_info("Exception as " % str(ex))

    def process_s3admin_request(self, request):
        """
        Process the request bundle request based on the command
        """
        access_key = request.selection_args.get('access_key', None)
        secret_key = request.selection_args.get('secret_key', None)
        self.client = get_client(access_key, secret_key, None, "iam")
        self.execute_command(request)

    def execute_command(self, request):
        """
        Execute thread based on s3user operation request from client.
        """

        action = request.selection_args.get('action', None)
        users_handler = UsersUtility(self.client, request.selection_args)

        if action == Strings.CREATE:
            deferred = deferToThread(users_handler.create())
            deferred.addCallback(self._handle_success, request)
            deferred.addErrback(self._handle_failure)
        elif action == Strings.LIST:
            deferred = deferToThread(users_handler.list())
            deferred.addCallback(self._handle_list_success, request)
            deferred.addErrback(self._handle_failure)
        elif action == Strings.REMOVE:
            deferred = deferToThread(users_handler.remove())
            deferred.addCallback(self._handle_remove_success, request)
            deferred.addErrback(self._handle_failure)
        elif action == Strings.MODIFY:
            deferred = deferToThread(users_handler.modify())
            deferred.addCallback(self._handle_modify_success, request)
            deferred.addErrback(self._handle_failure)

    def _handle_success(self, user_info, request):
        """Handle create operation response received from S3 server.

        This will be called when operation was successful.
        """

        response = S3CommandResponse()
        msg = response.get_response_message(Strings.CREATE, user_info)
        request.reply(msg)

    def _handle_list_success(self, users_info, request):
        """Handle list operation response received from S3 server.

        This will be called when operation was successful.
        """
        response = S3CommandResponse()
        msg = response.get_response_message(Strings.LIST, users_info)
        request.reply(msg)

    def _handle_modify_success(self, user_info, request):
        """Handle modify operation response received from S3 server.

        This will be called when operation was successful.
        """
        response = S3CommandResponse()
        msg = response.get_response_message(Strings.LIST, user_info)
        request.reply(msg)

    def _handle_remove_success(self, user_info, request):
        """Handle remove operation response received from S3 server.

        This will be called when operation was successful.
        """
        response = S3CommandResponse()
        msg = response.get_response_message(Strings.LIST, user_info)
        request.reply(msg)

    def _handle_failure(self, failure):
        """Handle failure case for  all operations.

        This will be called when operation was failed due to unknwon reasons.
        """
        self.log_info("Failed " + str(failure))
