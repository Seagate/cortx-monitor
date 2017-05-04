#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
File containing "s3admin account" command implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

import sys
from collections import OrderedDict

from cstor.cli.commands.base_command import BaseCommand
import cstor.cli.errors as errors
from cstor.cli.commands.s3commands.utils.utility import AccountKeys
from cstor.cli.commands.s3commands.utils.utility import _validate_email, \
    populate_credential_file, _validate_name, delete_credential_file
from cstor.cli.commands.utils.console import ConsoleTable
from cstor.cli.commands.utils.strings import Strings, Status


class S3AccountCommand(BaseCommand):
    def __init__(self, parser):
        """
        Initializes the power object with the
        arguments passed from CLI
        """
        # print parser
        super(S3AccountCommand, self).__init__()
        self.command = parser.command
        self.provider = Strings.PROVIDER
        self.action = parser.action
        if self.action == Strings.CREATE:
            self.name = parser.name
            self.email = parser.email
        if self.action == Strings.REMOVE:
            self.name = parser.account_name
            self.account_keys = AccountKeys(parser)
            self.force = parser.force

    @classmethod
    def description(cls):
        return 'Command for S3 Account related operations.'

    def get_action_params(self, **kwargs):
        """
        Power method to get the action parameters
        to be send in the request to data provider
        """
        params = '&command={}&action={}'.format(self.command, self.action)
        if self.action == Strings.CREATE:
            params += '&name={}&email={}'.format(self.name, self.email)
        elif self.action == Strings.REMOVE:
            params += '&name={}&force={}&access_key={}&secret_key={}'.format(
                self.name,
                self.force,
                self.account_keys.get_access_key(),
                self.account_keys.get_secret_key())
        return params

    @classmethod
    def arg_subparser(cls, subparsers):

        sp = subparsers.add_parser(
            'account', help=cls.description())

        sub_cmds = sp.add_subparsers(dest='action')
        sub_command = sub_cmds.add_parser(Strings.CREATE,
                                          help='Create new Account')

        sub_command.add_argument("-n", "--name", type=cls.validate_name,
                                 dest="name", required=True,
                                 help="Name of Account holder.")

        sub_command.add_argument("-e", "--email", type=cls.validate_email,
                                 dest="email", required=True,
                                 help="Email of Account holder")

        sub_cmds.add_parser(Strings.LIST, help="List all Accounts")
        remove_command = sub_cmds.add_parser(Strings.REMOVE,
                                             help="Remove Account")
        remove_command.add_argument("-n", "--name", dest="account_name",
                                    required=True,
                                    type=cls.validate_name,
                                    help="Account holder name.")
        remove_command.add_argument("-f", "--force", action='store_true',
                                    dest="force",
                                    help="Forcefully Remove Account")

        remove_command.add_argument("-k", "--access_key", dest="access_key",
                                    help="Access key of Root Account."
                                         "( Required if stored access_key "
                                         "does not found. )",
                                    required=False)
        remove_command.add_argument("-s", "--secret_key", dest="secret_key",
                                    help="Secret Key of Root Account."
                                         "( Required if stored secret_key "
                                         "does not found. )",
                                    required=False)

        sp.set_defaults(func=S3AccountCommand)

    @classmethod
    def validate_email(cls, value):
        """
        Validation of Email Account
        """
        return _validate_email(value)

    @classmethod
    def validate_name(cls, value):
        """
        Validation of name.
        """
        return _validate_name(value)

    def execute_action(self, **kwargs):
        # pylint:disable=too-many-function-args
        """
        Process the support_bundle response from the business layer
        """
        try:
            response = super(S3AccountCommand, self).execute_action(
                **kwargs)
            if self.action == Strings.CREATE:
                response = self.get_human_readable_response(self.name,
                                                            response)
            elif self.action == Strings.LIST:
                response = self.get_human_readable_list_response(response)
            elif self.action == Strings.REMOVE:
                response = self.get_human_readable_remove_response(self.name,
                                                                   response)

        except Exception as ex:
            if Strings.SOCKET_ERROR in str(ex):
                raise errors.InternalError(err=Strings.COMMUNICATION_ERROR,
                                           desc=Strings.COMMUNICATION_ER_DESC)
            raise errors.InternalError(desc=str(ex))
        return response

    @staticmethod
    def get_human_readable_response(name, result):
        response = result and result[0]
        message = response.get('message')
        status = message.get(Strings.STATUS)
        if status == 0:
            response = message.get("response")
            data = OrderedDict(
                [("Account ID", "AccountId"),
                 ("Access Key", "AccessKeyId"),
                 ("Secret Key", "RootSecretKeyId"),
                 ("Canonical Id", "CanonicalId")])

            writer = sys.stdout.write
            basic_table = ConsoleTable()
            basic_table.set_header(name='Name', value='Value')
            for key, value in data.items():
                data[key] = response.get(value)
                basic_table.append_row(name=key, value=data[key])
            bs_lines = basic_table.build('name', 'value')
            for line in bs_lines:
                writer(line + '\n')

            secret_key = data.get("Secret Key")
            access_key = data.get("Access Key")
            csv_data = [(Strings.ACCESS_KEY_ID, Strings.SECRET_KEY_ID),
                        (access_key, secret_key)
                        ]
            populate_credential_file(name, csv_data)
            return None
        else:
            data = Strings.CAN_NOT_PERFORM
            if status == Status.CONFLICT_STATUS:
                data += "Account already exist. Please enter another name."
            elif status == Status.SERVICE_UNAVAILABLE:
                data += "Service Unavailable."
            elif status == Status.BAD_REQUEST:
                data += "Bad Request. Invalid inputs provided."
            else:
                reason = message.get("reason")
                if reason is not None:
                    data += "{}".format(reason)
                else:
                    data += "Unable to create Account !"
        return data

    @staticmethod
    def get_human_readable_list_response(result):
        response = result and result[0]
        message = response.get('message')
        status = message.get("status")
        if status == 0:
            writer = sys.stdout.write
            response = message.get("response")
            if response is None:
                data = "Status: No Accounts found !!"
                return data

            accounts = response['member']
            basic_table = ConsoleTable()
            basic_table.set_header(name='Name', email='Email',
                                   accountId='Account ID',
                                   canonicalId='Canonical Id')
            if type(accounts) == dict:
                basic_table.append_row(name=accounts.get('AccountName'),
                                       email=accounts.get('Email'),
                                       accountId=accounts.get('AccountId'),
                                       canonicalId=accounts.get('CanonicalId'))
            else:
                for account in accounts:
                    basic_table.append_row(name=account.get('AccountName'),
                                           email=account.get('Email'),
                                           accountId=account.get('AccountId'),
                                           canonicalId=account.get(
                                               'CanonicalId'))
            bs_lines = basic_table.build('name', 'email', 'accountId',
                                         'canonicalId')
            for line in bs_lines:
                writer(line + '\n')
            return None
        else:

            data = Strings.CAN_NOT_PERFORM
            if status == Status.SERVICE_UNAVAILABLE:
                data += "Service Unavailable."
            else:
                reason = message.get("reason")
                if reason is not None:
                    data += "{}".format(reason)
                else:
                    data += "Unable to list Accounts !"

        return data

    @staticmethod
    def get_human_readable_remove_response(name, result):
        response = result and result[0]
        message = response.get('message')
        status = message.get("status")
        if status == 0:
            data = "Status: Success\nDetails: Account Removed successfully !"
            delete_credential_file(name)
            return data
        else:
            data = Strings.CAN_NOT_PERFORM
            if status == Status.SERVICE_UNAVAILABLE:
                data += "Service Unavailable."
            elif status == Status.NOT_FOUND:
                data += "Account does not exist."
            elif status == Status.CONFLICT_STATUS:
                data += "Account can not be removed as " \
                        "It have associated Users and Access Keys. " \
                        "\nPlease use --force option to remove Account."
            elif status == Status.UNAUTHORIZED:
                data += "Unauthorized Access. " \
                        "Please enter valid Access key and Secret Key."
            else:
                reason = message.get("reason")
                if reason is not None:
                    data += "{}".format(reason)
                else:
                    data += "Unable to remove Account !"

        return data
