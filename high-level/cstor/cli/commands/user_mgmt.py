#!/usr/bin/python
# -*- coding: utf-8 -*-

"""File containing "user management" sub command implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# __author__ = Bhupesh Pant

from cstor.cli import errors
from cstor.cli.commands.base_command import BaseCommand
from cstor.cli.commands.utils.strings import UserHelpStr
from cstor.cli.errors import InvalidArgumentError
from cstor.cli.settings import DEBUG


class UserMgmt(BaseCommand):
    """Client for querying user_mgmt interface in PLEX"""

    def __init__(self, parser):
        super(UserMgmt, self).__init__()
        self.provider = 'user_mgmt'
        self.action = parser.action
        if self.action == 'create':
            self.username = parser.username
            self.password = parser.pwd
            self.components = parser.components
        elif self.action == 'remove':
            self.username = parser.username
        else:
            print 'Unknown Command Supplied: ', self.action
            raise InvalidArgumentError()

    def get_action_params(self, **kwargs):
        """
        Status method to get the command uri part
        """
        params = '&command={}'.format(self.action)
        if self.action == 'create':
            params = '{}&user={}&pwd={}&components={}'.format(
                params, self.username, self.password,
                ','.join(self.components)
            )
        elif self.action == 'remove':
            params = '{}&user={}&pwd=None&components=None'.\
                format(params, self.username)
        return params

    @staticmethod
    def add_args(subparsers):
        """
        Defines the command structure for power command
        """
        user_mgmt = subparsers.add_parser('user',
                                          help=UserHelpStr.help)
        sub_cmds = user_mgmt.add_subparsers(dest='action')
        # Create command param'
        create_cmd = sub_cmds.add_parser('create',
                                         help=UserHelpStr.create)
        create_cmd.add_argument('-u', '--username', dest="username",
                                required=True, help=UserHelpStr.name)
        create_cmd.add_argument('-p', '--password', dest="pwd",
                                required=True, help=UserHelpStr.password)
        create_cmd.add_argument('-c', '--capabilities',
                                dest="components",
                                help=UserHelpStr.components,
                                nargs='*',
                                choices=['ras', 'fs-tools', 's3', 'fs-gui',
                                         'seastream', 'fs-cli', 'root'])
        # Remove command params
        remove_cmd = sub_cmds.add_parser('remove', help=UserHelpStr.remove)
        remove_cmd.add_argument('-u', '--username',
                                dest="username", required=True,
                                help=UserHelpStr.name)
        remove_cmd.add_argument('-f', '--force', action='store_true',
                                help=UserHelpStr.force_remove)
        user_mgmt.set_defaults(func=UserMgmt)

    def execute_action(self, **kwargs):
        """
        Process the support_bundle response from the business layer
        """
        # pylint:disable=too-many-function-args
        try:
            response_data = super(UserMgmt, self).execute_action(**kwargs)
            response_str = self.get_human_readable_response(response_data)
        # pylint:disable=broad-except
        except Exception:
            raise errors.InternalError()
        return response_str

    def get_human_readable_response(self, response_data):
        """Formats the provider response into human readable response."""
        response_data = response_data[-1]
        command = response_data.get('command')
        user_info = response_data.get('user_info')
        if response_data.get('return_code') == 0:
            response = 'User: {} is successfully {}d'.format(
                user_info.get('username'), command)
            if command == 'create':
                response = '{} and authorized for {}'.format(
                    response,
                    user_info.get('components')
                )
        else:
            response = '{} User: {} FAILED.\n Please refer ' \
                       '/var/log/plex_clusterstor.log for more info about ' \
                       'the failure.'.format(command, user_info.get(
                                             'username'))
        return response
