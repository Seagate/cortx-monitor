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
        self.action = parser.command

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for HA command
        """

        ha_parser = subparsers.add_parser('ha',
                                          help='Subcommand to work '
                                          ' with HA component of cluster.')
        ha_parser.add_argument('command', help='Command to run.',
                               choices=['debug', 'show'])
        ha_parser.set_defaults(func=Ha)

    def get_provider_base_url(self):
        """ Abstract method to get the base url for
        the resource specific data provider
        """
        # This function needs node specific implementation

    def get_action_params(self):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """
        # This function needs node specific implementation
