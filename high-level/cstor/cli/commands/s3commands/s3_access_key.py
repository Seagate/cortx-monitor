import sys

from cstor.cli.commands.base_command import BaseCommand
from cstor.cli.commands.s3commands.utils.utility import AccountKeys
import cstor.cli.errors as errors
from cstor.cli.commands.utils.console import ConsoleTable
from cstor.cli.commands.utils.strings import Strings, Status


class S3AccessKeyCommand(BaseCommand):
    def __init__(self, parser):
        """
            Initializes the power object with the
            arguments passed from CLI
        """
        # print parser
        super(S3AccessKeyCommand, self).__init__()
        self.command = parser.command
        self.provider = Strings.PROVIDER
        self.action = parser.action
        self.account_keys = AccountKeys(parser)
        self.user_name = parser.name
        if self.action == Strings.REMOVE or self.action == Strings.MODIFY:
            self.user_access_key = parser.user_access_key
            if self.action == Strings.MODIFY:
                self.status = parser.status

    @classmethod
    def description(cls):
        return 'Command for S3 Access Key related operations.'

    def get_action_params(self, **kwargs):
        """
        Power method to get the action parameters
        to be send in the request to data provider
        """
        # print "get_action_params called"
        params = "&command={}&action={}&access_key={}&secret_key={}".format(
            self.command, self.action,
            self.account_keys.get_access_key(),
            self.account_keys.get_secret_key())

        params += '&user_name={}'.format(self.user_name)
        if self.action == Strings.REMOVE or self.action == Strings.MODIFY:
            params += '&user_access_key={}'.format(self.user_access_key)
            if self.action == Strings.MODIFY:
                params += '&status={}'.format(self.status)

        return params

    @classmethod
    def arg_subparser(cls, subparsers):

        sp = subparsers.add_parser(
            'access_key', help=cls.description())

        sub_cmds = sp.add_subparsers(dest='action')
        common_usage = "\t\t(-a ACCOUNT_NAME | -s SECRET_KEY -k ACCESS_KEY)"
        create_usage = "cstor s3admin access_key create [-h] -u USER_NAME \n"
        create_usage += common_usage

        sub_command = sub_cmds.add_parser(Strings.CREATE, usage=create_usage,
                                          help='Create new Access key for '
                                               'Particular User')

        sub_command.add_argument("-u", "--user_name", dest="name",
                                 required=True,
                                 help="Name of User.")
        cls.add_common_arguments(sub_command)

        list_usage = "cstor s3admin access_key list [-h] -u USER_NAME\n"
        list_usage += common_usage
        list_command = sub_cmds.add_parser(Strings.LIST,
                                           help="List all Access keys of "
                                                "Particular User",
                                           usage=list_usage)
        list_command.add_argument("-u", "--user_name", dest="name",
                                  required=True,
                                  help="Name of User.")
        cls.add_common_arguments(list_command)

        update_usage = "cstor s3admin access_key modify [-h] " \
                       "-K USER_ACCESS_KEY -u USER_NAME\n " \
                       "-t {Active, Inactive}\n"
        update_usage += common_usage
        update_command = sub_cmds.add_parser(Strings.MODIFY,
                                             help="Modify Access Key for "
                                                  "Particular User",
                                             usage=update_usage)
        update_command.add_argument("-K", "--user_access_key",
                                    dest="user_access_key", required=True,
                                    help="Access Key to be Updated")
        update_command.add_argument("-u", "--user_name", dest="name",
                                    required=True, help="Name of User")
        update_command.add_argument("-t", "--status",
                                    choices=['Active', 'Inactive'],
                                    dest="status", required=True,
                                    help="Status of Access key")
        cls.add_common_arguments(update_command)

        delete_usage = "cstor s3admin access_key remove [-h] " \
                       "-K USER_ACCESS_KEY -u USER_NAME\n"
        delete_usage += common_usage
        delete_command = sub_cmds.add_parser(Strings.REMOVE,
                                             help="Remove Access Key for "
                                                  "Particular User",
                                             usage=delete_usage)
        delete_command.add_argument("-K", "--user_access_key",
                                    dest="user_access_key", required=True,
                                    help="Access Key to be Deleted")
        delete_command.add_argument("-u", "--user_name", dest="name",
                                    required=True, help="Name of User")
        cls.add_common_arguments(delete_command)

        sp.set_defaults(func=S3AccessKeyCommand)

    @classmethod
    def add_common_arguments(cls, command):
        """Following are common arguments for all subcommands."""

        command.add_argument("-a", "--account", dest="account_name",
                             help="Account holder name.")
        command.add_argument("-k", "--access_key", dest="access_key",
                             help="Access key of Root Account.")
        command.add_argument("-s", "--secret_key", dest="secret_key",
                             help="Secret Key of Root Account.")

    def execute_action(self, **kwargs):
        # pylint:disable=too-many-function-args
        """
        Process the operation response from the business layer
        """
        # print "execute_action called"
        try:
            response = super(S3AccessKeyCommand, self).execute_action(
                **kwargs)
            if self.action == Strings.CREATE:
                response = self.get_human_readable_response(response)
            elif self.action == Strings.LIST:
                response = self.get_human_readable_list_response(response)
            elif self.action == Strings.MODIFY:
                response = self.get_human_readable_modify_response(response)
            elif self.action == Strings.REMOVE:
                response = self.get_human_readable_remove_response(response)

        except Exception:
            raise errors.InternalError()
        return response

    @staticmethod
    def get_human_readable_response(result):
        """
        Convert create operation response.

        It will convert create operation response returned from Business layer
        to human readable response.
        """
        response = result and result[0]
        message = response.get('message')
        if message.get("status") == 0:
            writer = sys.stdout.write
            response = message.get("response").get("AccessKey")
            data = {"User Name": "UserName", "Status": "Status",
                    "Access Key": "AccessKeyId",
                    "Secret Key": "SecretAccessKey"}

            basic_table = ConsoleTable()
            basic_table.set_header(name='Name', value='Value')
            for key in data.keys():
                data[key] = response.get(data.get(key))
                basic_table.append_row(name=key, value=data[key])
            bs_lines = basic_table.build('name', 'value')
            for line in bs_lines:
                writer(line + '\n')
            return None
        else:
            data = S3AccessKeyCommand.handle_failure_conditions(message,
                                                                Strings.CREATE)
        return data

    @staticmethod
    def get_human_readable_remove_response(result):
        """
        Convert remove operation response.

        It will convert remove operation response returned from Business layer
        to human readable response.
        """
        response = result and result[0]
        message = response.get('message')
        if message.get("status") == 0:
            data = "Status: Success.\nDetails: " \
                   "Access Key removed Successfully !!"
        else:
            data = S3AccessKeyCommand.handle_failure_conditions(message,
                                                                Strings.REMOVE)
        return data

    @staticmethod
    def get_human_readable_modify_response(result):
        """
        Convert modify operation response.

        It will convert modify operation response returned from Business layer
        to human readable response.
        """
        response = result and result[0]
        message = response.get('message')
        if message.get("status") == 0:
            data = "Status: Success.\nDetails: " \
                   "Access Key updated Successfully !!"
        else:
            data = S3AccessKeyCommand.handle_failure_conditions(message,
                                                                Strings.MODIFY)
        return data

    @staticmethod
    def get_human_readable_list_response(result):
        """
        Convert list operation response.

        It will convert list operation response returned from Plex to human
        readable response.
        """
        response = result and result[0]
        message = response.get('message')
        if message.get("status") == 0:
            writer = sys.stdout.write
            response = message.get("response")

            # Check if empty list returned.
            accounts = response['AccessKeyMetadata']
            if not accounts:
                data = "Status: No Access keys associated for User !!"
                return data

            basic_table = ConsoleTable()
            basic_table.set_header(name='User Name', status='Status',
                                   access_key='Access Key')
            if type(accounts) == dict:
                basic_table.append_row(name=accounts.get('UserName'),
                                       status=accounts.get('Status'),
                                       access_key=accounts.get('AccessKeyId'))
            else:
                for account in accounts:
                    basic_table.append_row(name=account.get('UserName'),
                                           status=account.get('Status'),
                                           access_key=account.get(
                                               'AccessKeyId'))
            bs_lines = basic_table.build('name', 'status', 'access_key')
            for line in bs_lines:
                writer(line + '\n')
            return None
        else:
            data = S3AccessKeyCommand.handle_failure_conditions(message,
                                                                Strings.LIST)
        return data

    @staticmethod
    def handle_failure_conditions(message, operation):
        """Handle various failure conditions for all operations."""

        status = message.get(Strings.STATUS)
        data = Strings.CAN_NOT_PERFORM
        if status == Status.NOT_FOUND:
            if operation == Strings.LIST or operation == Strings.CREATE:
                data += "User does not exist. Please enter valid user name."
            else:
                data += "Access key/User does not exist. " \
                        "Please enter another valid Access Key/User."
        elif status == Status.UNAUTHORIZED:
            data += "Unauthorized Access. Either Invalid Access key or" \
                    " Secret key entered."
        elif status == Status.SERVICE_UNAVAILABLE:
            data += "Service Unavailable."
        elif status == Status.SERVICE_UNAVAILABLE:
            data += "Service Unavailable."
        elif status == Status.BAD_REQUEST:
            data += "Maximum two Access Keys can be allocated to each User."
        else:
            reason = message.get("reason")
            if reason is not None:
                data += "{}".format(reason)
            else:
                data += "Unable to perform {}!".format(operation)
        return data
