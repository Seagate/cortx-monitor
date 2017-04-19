from twisted.internet.threads import deferToThread

from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.s3admin.s3_utils import get_client
from sspl_hl.utils.s3admin.access_key_handler import AccessKeyUtility
from sspl_hl.utils.message_utils import S3CommandResponse
from sspl_hl.utils.s3admin.s3_utils import Strings


class S3AccessKeyProvider(BaseCastorProvider):
    def __init__(self, name, description):
        super(S3AccessKeyProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command', 'action', 'user_name', 'access_key',
                               'secret_key', 'user_access_key', 'status']
        self.valid_commands = ['access_key']
        self.valid_subcommands = [Strings.CREATE, Strings.LIST, Strings.MODIFY,
                                  Strings.REMOVE]
        self.mandatory_args = ['command', 'action', 'access_key', 'secret_key',
                               'user_name']
        self.no_of_arguments = 7
        self.client = None
        self.action = None

    def handleRequest(self, request):
        """Request Handler

        This method get called from Parent class render_query when entered
        values are correct.
        """
        try:
            self.render_query(request)
        except Exception as ex:
            print str(ex)

    def render_query(self, request):
        """
        S3 Account request handler.
        """
        self.action = request.selection_args.get('action', None)
        if self.action == Strings.REMOVE:
            self.no_of_arguments = 6
        if not super(S3AccessKeyProvider, self).render_query(request):
            return
        self.process_s3auth_request(request)

    def process_s3auth_request(self, request):
        """
        Process the request bundle request based on the command
        """
        access_key = request.selection_args.get(Strings.ACCESS_KEY, None)
        secret_key = request.selection_args.get(Strings.SECRET_KEY, None)
        self.client, response = get_client(access_key, secret_key,
                                           Strings.IAM_SERVICE)
        if self.client is None:
            request.reply(S3CommandResponse().get_response_message(response))
        else:
            self.execute_command(request)

    def execute_command(self, request):
        """
        Execute thread based on s3access_key operation request from client.
        """

        action = request.selection_args.get('action', None)
        handler = AccessKeyUtility(self.client, request.selection_args)
        if action == Strings.CREATE:
            deferred = deferToThread(handler.create())
        elif action == Strings.LIST:
            deferred = deferToThread(handler.list())
        elif action == Strings.MODIFY:
            deferred = deferToThread(handler.modify())
        elif action == Strings.REMOVE:
            deferred = deferToThread(handler.remove())
        deferred.addCallback(self._handle_success, request)
        deferred.addErrback(self._handle_failure)

    def _handle_success(self, access_key_info, request):
        """Handle operation response received from S3 server.

        This will be called when operation was successful.
        """
        response = S3CommandResponse()
        msg = response.get_response_message(access_key_info)
        request.reply(msg)

    def _handle_failure(self, failure):
        """Handle failure case for  all operations.

        This will be called when operation was failed due to unknwon reasons.
        """
        self.log_info("Failed " + str(failure))
