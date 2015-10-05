#!/usr/bin/python
# -*- coding: utf-8 -*-

""" File containing "ldap" command implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

import argparse

# Import Local Modules
from cstor.cli.commands.base_command import BaseCommand


class LdapAdmin(BaseCommand):

    """ LDAP admin command implementation class
    """

    def __init__(self, parser):
        """ Initializes the LDAP object with the
        arguments passed from CLI
        """

        super(LdapAdmin, self).__init__()
        self.command = parser.command
        self.subcommand = parser.subcommand
        if 'user_name' in parser:
            self.user = parser.user_name
        else:
            self.user = None

        self.provider = 'ldap'

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for admin command
        """
        parent_admin_parser = argparse.ArgumentParser(add_help=False)

        parent_admin_parser.add_argument('user_name',
                                         help='username for admin command')

        admin_parser = subparsers.add_parser('admin',
                                             help='ldap admin command')
        admin_parser.add_argument('command', help='command action for ldap.',
                                  choices=['user'])
        action_parser = admin_parser.add_subparsers(dest='subcommand',
                                                    help='subcommand for \
ldap action')
        action_parser.add_parser('show', parents=[parent_admin_parser])
        action_parser.add_parser('list')
        admin_parser.set_defaults(func=LdapAdmin)

    def get_action_params(self, **kwargs):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """
        if self.command == 'user' and self.subcommand == 'list':
            self.user = 'all'
        params = 'command={}&subcommand={}&user={}'.format(self.command,
                                                           self.subcommand,
                                                           self.user)
        return params
