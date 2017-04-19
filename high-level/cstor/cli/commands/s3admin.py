#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
File containing "s3admin" command implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

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
