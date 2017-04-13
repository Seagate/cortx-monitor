import sys

from cstor.cli.commands.utils.strings import Strings, Status
from cstor.cli.commands.utils.console import ConsoleTable
from cstor.cli.commands.base_command import BaseCommand
from cstor.cli.commands.s3commands.utils.utility import AccountKeys
import cstor.cli.errors as errors


class S3UsersCommand(BaseCommand):
    def __init__(self, parser):
        """
            Initializes the power object with the
            arguments passed from CLI
        """
        # print parser
        super(S3UsersCommand, self).__init__()
        self.command = parser.command
        self.provider = Strings.PROVIDER
        self.action = parser.action
        self.account_keys = AccountKeys(parser)
        if self.action != Strings.LIST:
            self.name = parser.name
            if self.action == Strings.MODIFY:
                self.new_name = parser.new_name
            if self.action != Strings.REMOVE:
                self.path = parser.path

    @classmethod
    def description(cls):
        return 'Command for S3 User related operations.'

    def get_action_params(self, **kwargs):
        """
        Method to get the action parameters
        to be send in the request to data provider
        """
        try:
            params = '&command={}&action={}&access_key={}&secret_key={}' \
                .format(self.command, self.action,
                        self.account_keys.get_access_key(),
                        self.account_keys.get_secret_key())
            if self.action != Strings.LIST:
                params += '&name={}'.format(self.name)
                if self.action == Strings.MODIFY:
                    params += '&new_name={}'.format(self.new_name)
                if self.action != Strings.REMOVE:
                    if self.path is not None:
                        params += '&path={}'.format(self.path)

            return params
        except Exception as ex:
            print(str(ex))

    @classmethod
    def arg_subparser(cls, subparsers):

        sp = subparsers.add_parser(
            'user', help=cls.description())

        sub_cmds = sp.add_subparsers(dest='action')
        create_usage = "cstor s3admin user create [-h] -u USER_NAME [-p PATH]\
                             \n(-a ACCOUNT_NAME | -s SECRET_KEY -k ACCESS_KEY)"
        create_command = sub_cmds.add_parser(Strings.CREATE,
                                             help='Create new User',
                                             usage=create_usage)

        create_command.add_argument("-u", "--user_name", dest="name",
                                    required=True,
                                    help="Name of User.")
        create_command.add_argument("-p", "--path", dest="path",
                                    required=False,
                                    help="Path for User (Optional)")
        cls.add_common_arguments(create_command)

        list_usage = "cstor s3admin user list [-h] (-a account |" \
                     " -s SECRET_KEY -k ACCESS_KEY)"

        list_command = sub_cmds.add_parser(Strings.LIST, help="List all Users",
                                           usage=list_usage)
        cls.add_common_arguments(list_command)

        update_usage = "cstor s3admin user modify [-h] -o OLD_USER_NAME " \
                       "-n NEW_USER_NAME [-p NEW_PATH]\n " \
                       "(-a ACCOUNT_NAME | -s SECRET_KEY -k ACCESS_KEY)"

        update_command = sub_cmds.add_parser(Strings.MODIFY,
                                             help="Modify User",
                                             usage=update_usage)
        update_command.add_argument("-o", "--old_user_name", dest="name",
                                    required=True, help="Old Name of User")
        update_command.add_argument("-u", "--new_user_name", dest="new_name",
                                    required=True, help="New Name of User")
        update_command.add_argument("-p", "--new_path", dest="path",
                                    required=False,
                                    help="New path for User (Optional)")

        cls.add_common_arguments(update_command)

        delete_usage = "cstor s3admin user remove [-h] -u USER_NAME \n" \
                       "(-a ACCOUNT_NAME | -s SECRET_KEY -k ACCESS_KEY)"
        delete_command = sub_cmds.add_parser(Strings.REMOVE,
                                             help="Remove User",
                                             usage=delete_usage)
        delete_command.add_argument("-u", "--user_name", dest="name",
                                    required=True, help="Name of User")
        cls.add_common_arguments(delete_command)

        sp.set_defaults(func=S3UsersCommand)

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
        Process the s3users response from the business layer
        """
        # print "execute_action called"
        try:
            response = super(S3UsersCommand, self).execute_action(**kwargs)
            if self.action == Strings.CREATE:
                response = self.get_human_readable_response(response)
            elif self.action == Strings.LIST:
                response = self.get_human_readable_list_response(response)
            elif self.action == Strings.MODIFY:
                response = self.get_human_readable_modify_response(response)
            elif self.action == Strings.REMOVE:
                response = self.get_human_readable_remove_response(response)

        except Exception as ex:
            print str(ex)
            raise errors.InternalError()
        return response

    @staticmethod
    def get_human_readable_response(result):
        """Convert create operation response to human readable response."""
        response = result and result[0]
        message = response.get('message')
        status = message.get(Strings.STATUS)
        if status == 0:
            response = message.get("response").get("User")
            data = {"User Name": "UserName", "Path": "Path",
                    "User ID": "UserId",
                    "ARN": "Arn"}

            writer = sys.stdout.write
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
            return S3UsersCommand.handle_failure_conditions(message,
                                                            Strings.CREATE)

    @staticmethod
    def get_human_readable_remove_response(result):
        """Convert remove operation response to human readable response."""
        response = result and result[0]
        message = response.get('message')
        status = message.get(Strings.STATUS)
        if status == 0:
            data = "Status: Success.\nDetails: User removed Successfully !!"
        else:
            data = S3UsersCommand.handle_failure_conditions(message,
                                                            Strings.REMOVE)
        return data

    @staticmethod
    def get_human_readable_modify_response(result):
        """Convert modify response to human readable response."""
        response = result and result[0]
        message = response.get('message')
        status = message.get(Strings.STATUS)
        if status == 0:
            data = "Status: Success.\nDetails: User modified Successfully !!"
        else:
            data = S3UsersCommand.handle_failure_conditions(message,
                                                            Strings.MODIFY)
        return data

    @staticmethod
    def get_human_readable_list_response(result):
        """Convert list response to human readable response."""
        response = result and result[0]
        message = response.get('message')
        status = message.get(Strings.STATUS)
        if status == 0:
            response = message.get("response")
            if response is None:
                data = "Status: No Users found !!"
                return data

            writer = sys.stdout.write
            users = response['Users']
            basic_table = ConsoleTable()
            basic_table.set_header(name='User Name', user_id='User ID',
                                   arn='ARN', path='Path')
            if type(users) == dict:
                basic_table.append_row(name=users.get('UserName'),
                                       user_id=users.get('UserId'),
                                       arn=users.get('Arn'),
                                       path=users.get('Path'))
            else:
                for user in users:
                    basic_table.append_row(name=user.get('UserName'),
                                           user_id=user.get('UserId'),
                                           arn=user.get('Arn'),
                                           path=user.get('Path'))
            bs_lines = basic_table.build('name', 'user_id', 'arn', 'path')
            for line in bs_lines:
                writer(line + '\n')
            return None
        else:
            data = S3UsersCommand.handle_failure_conditions(message,
                                                            Strings.LIST)
        return data

    @staticmethod
    def handle_failure_conditions(message, operation):
        """Handle various failure conditions for all operations."""

        status = message.get(Strings.STATUS)
        data = Strings.CAN_NOT_PERFORM
        if status == Status.NOT_FOUND:
            data += "User does not exist. Please enter another User Name."
        elif status == Status.CONFLICT_STATUS:
            data += "User already exist. Please enter another User Name."
        elif status == Status.UNAUTHORIZED:
            data += "Unauthorized Access. Either Invalid Access key or" \
                    " Secret key entered."
        elif status == Status.SERVICE_UNAVAILABLE:
            data += "Service Unavailable."
        else:
            reason = message.get("reason")
            if reason is not None:
                data = "{}".format(reason)
            else:
                data = "Unable to {} Account !".format(operation)
        return data
