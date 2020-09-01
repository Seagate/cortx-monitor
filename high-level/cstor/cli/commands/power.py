#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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


"""File containing "power" sub command implementation
"""

# Third Party
# Import Local Modules
from cstor.cli.commands.base_command import BaseCommand
from cstor.cli.errors import CommandTerminated
from cstor.cli.settings import DEBUG
import cstor.cli.errors as errors


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
        print 'This may take some time depending upon your ' \
              'network configuration...'

    def get_action_params(self, **kwargs):
        """
        Power method to get the action parameters
        to be send in the request to data provider
        """
        return '&command={}&debug={}'.format(self.action, DEBUG)

    @staticmethod
    def add_args(subparsers):
        """
        Defines the command structure for power command
        """
        power_parser = subparsers.add_parser('power',
                                             help='Sub-command to work with '
                                                  'power of all the nodes.')
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
                                  " all the nodes (y/n)")
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

    def execute_action(self, **kwargs):
        # pylint:disable=too-many-function-args
        """
        Process the support_bundle response from the business layer
        """
        try:
            response_data = super(Power, self).execute_action(**kwargs)
            response_str = self.get_human_readable_response(response_data)
        # pylint:disable=broad-except
        except Exception:
            raise errors.InternalError()
        return response_str

    @staticmethod
    def get_human_readable_response(result):
        """
        Parse the json to read the human readable response
        """
        response = 'An Internal error has occurred, unable to complete ' \
                   'command.'
        result = result and result[-1]
        response = result.get('power_commands_reply', response)
        return response
