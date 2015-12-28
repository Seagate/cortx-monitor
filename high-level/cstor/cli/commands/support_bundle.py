#!/usr/bin/python
# -*- coding: utf-8 -*-

""" File containing " support_bundle" command implementation
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


class SupportBundle(BaseCommand):

    """ support_bundle command implementation class
    """

    def __init__(self, parser):
        """ Initializes the bundle object with the
        arguments passed from CLI
        """

        super(SupportBundle, self).__init__()
        self.command = parser.command
        self.provider = "support_bundle"

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for support_bundle command
        """

        sb_parser = subparsers.add_parser('support_bundle',
                                          help='Sub-command \
        to work on support related operations')

        sb_parser.add_argument('command', help='command \
            to run', choices=['create', 'list'])

        sb_parser.set_defaults(func=SupportBundle)

    def get_action_params(self, **kwargs):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """
        params = 'command={}'.format(self.command)
        return params
