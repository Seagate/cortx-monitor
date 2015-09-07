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
import argparse

# Import Local Modules
from cstor.cli.commands.node import Node
from cstor.cli.errors import CommandTerminated

CURRENT_NODE = "LOCAL_NODE"


class Power(Node):
    """
        Power command implementation class
    """

    def __init__(self, parser):
        """
            Initializes the power object with the
            arguments passed from CLI
        """
        if parser.action == 'off':
            Power.handle_power_off_cases(parser)
        super(Power, self).__init__(parser)
        self.provider = 'power'

    @staticmethod
    def add_args(subparsers):
        """
            defines the command structure for power command
        """
        parent_cmd_parser = argparse.ArgumentParser(add_help=False)
        parent_cmd_parser.add_argument('--node_spec',
                                       help='Optional parameter to indicate'
                                            ' the Regex for nodes that '
                                            'should be affected.')
        power_parser = subparsers.add_parser('power',
                                             help='Sub-command to work with '
                                                  'power of the cluster.')
        sub_cmds = power_parser.add_subparsers(dest='action',
                                               help='command to run')
        sub_cmds.add_parser('on', parents=[parent_cmd_parser])
        off_cmd = sub_cmds.add_parser('off', parents=[parent_cmd_parser])
        off_cmd.add_argument('-f', '--force', action='store_true',
                             help='Forcing off may lead to data loss. I know '
                                  'what I am doing and I won\'t blame Seagate'
                                  ' for it')
        sub_cmds.add_parser('status', parents=[parent_cmd_parser])
        power_parser.set_defaults(func=Power)

    @staticmethod
    def handle_power_off_cases(parser):
        """
            check the power off params and conditions for the command
        """
        if not (parser.force or parser.node_spec):
            if parser.node_spec == CURRENT_NODE:
                usr_input = raw_input("Are you sure you want to power off"
                                      " the current node (y/n)")
            else:
                usr_input = raw_input("Are you sure you want to power off"
                                      " all the node (y/n)")
            Power.check_user_input(usr_input)
        return

    @staticmethod
    def check_user_input(usr_input):
        """
            validate the user input and if needed poll for the correct input
        """
        usr_input = usr_input.upper()
        if usr_input in ['N', 'NO']:
            raise CommandTerminated()
        elif usr_input in ['Y', 'YES']:
            return
        else:
            usr_input = raw_input("Please enter (y/n)")
            Power.check_user_input(usr_input)
