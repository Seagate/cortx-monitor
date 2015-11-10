#!/usr/bin/python
# -*- coding: utf-8 -*-

"""File containing "power" sub command implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

# Third Party
# Import Local Modules
from cstor.cli.commands.base_command import BaseCommand
from cstor.cli.errors import CommandTerminated
from cstor.cli.settings import DEBUG

CURRENT_NODE = "LOCAL_NODE"


class Power(BaseCommand):
    """
    Power command implementation class
    """

    def __init__(self, parser):
        """
            Initializes the power object with the
            arguments passed from CLI
        """
        if 'action' in parser:
            self.action = parser.action
        else:
            self.action = None

        if parser.action == 'off':
            Power.handle_power_off_cases(parser)
        super(Power, self).__init__()
        self.provider = 'power'

    def get_action_params(self, **kwargs):
        """
        Power method to get the action parameters
        to be send in the request to data provider
        """
        params = '&command={}&debug={}'.format(self.action,
                                               DEBUG)
        return params

    @staticmethod
    def add_args(subparsers):
        """
        Defines the command structure for power command
        """
        power_parser = subparsers.add_parser('power',
                                             help='Sub-command to work with '
                                                  'power of the cluster.')
        sub_cmds = power_parser.add_subparsers(dest='action',
                                               help='command to run')
        sub_cmds.add_parser('on',
                            help='Power on all the SSUs in the cluster')
        off_cmd = sub_cmds.add_parser('off',
                                      help='Power off all the SSUs in '
                                           'the cluster')
        off_cmd.add_argument('-f', '--force', action='store_true',
                             help='Forcing off may lead to data loss. I '
                                  'know what I am doing and I won\'t '
                                  'blame SeaGate for it')
        power_parser.set_defaults(func=Power)

    @staticmethod
    def handle_power_off_cases(parser):
        """
        Check the power off params and conditions for the command
        """

        if not parser.force:
            usr_input = raw_input("Are you sure you want to power off"
                                  " all the node (y/n)")
            Power.check_user_input(usr_input)

    @staticmethod
    def check_user_input(usr_input):
        """
        Validate the user input and if needed poll for the correct input
        """
        usr_input = usr_input.upper()
        if usr_input in ['N', 'NO']:
            raise CommandTerminated()
        elif usr_input in ['Y', 'YES']:
            return
        else:
            usr_input = raw_input("Please enter (y/n)")
            Power.check_user_input(usr_input)
