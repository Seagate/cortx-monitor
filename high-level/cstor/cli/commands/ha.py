#!/usr/bin/python
# -*- coding: utf-8 -*-

""" File containing "ha" sub command implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

# Import Local Modules

from cstor.cli.commands.base_command import BaseCommand


class Ha(BaseCommand):

    """ HA command implementation class
    """

    def __init__(self, parser):
        """ Initializes the HA object with the
        arguments passed from CLI
        """

        super(Ha, self).__init__()
        self.level = parser.level
        self.command = parser.command
        self.provider = 'ha'

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for HA command
        """

        ha_parser = subparsers.add_parser('ha',
                                          help='Subcommand to work '
                                          ' with HA component of cluster.')

        ha_parser.add_argument('level', help='Verbosity level of the command.',
                               choices=['info', 'debug'])

        ha_parser.add_argument('command', help='Command to run.',
                               choices=['status', 'show'])

        ha_parser.set_defaults(func=Ha)

    def get_action_params(self):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """
        params = 'level={}&command={}'.format(self.level, self.command)
        return params
