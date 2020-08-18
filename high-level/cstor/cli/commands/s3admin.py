#!/usr/bin/python
# -*- coding: utf-8 -*-

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


"""
File containing "s3admin" command implementation
"""

from cstor.cli.commands.base_command import BaseCommand


class S3Admin(BaseCommand):
    """ s3admin command implementation class
    """

    def __init__(self, parser):
        """ Initializes the admin object with the
        arguments passed from CLI
        """

        super(S3Admin, self).__init__()
        self.command = parser.command

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for s3admin command
        """

        sb_parser = subparsers.add_parser('s3admin',
                                          help='Sub-command \
        to work on s3 user management related operations.')
        sub = sb_parser.add_subparsers(dest='command')
        # s3 commands
        try:
            from cstor.cli.commands.s3commands.s3_account \
                import S3AccountCommand

            S3AccountCommand.arg_subparser(sub)

            from cstor.cli.commands.s3commands.s3_users \
                import S3UsersCommand
            S3UsersCommand.arg_subparser(sub)

            from cstor.cli.commands.s3commands.s3_access_key \
                import S3AccessKeyCommand
            S3AccessKeyCommand.arg_subparser(sub)

        except ImportError:
            pass

    def handler(self, args):
        """Given command depends on sub-commands, so let's pass
        flow control to them using .func() callback"""
        args.func(args)
