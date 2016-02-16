#!/usr/bin/python
# -*- coding: utf-8 -*-

"""File containing "status" sub command implementation
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
from cstor.cli.settings import DEBUG


class Status(BaseCommand):
    """
    Power command implementation class
    """

    def __init__(self, parser):
        """
            Initializes the power object with the
            arguments passed from CLI
        """
        super(Status, self).__init__()
        self.action = 'ipmi'
        self.parser = parser
        self.provider = 'status'
        print 'This may take some time depending upon your ' \
              'network configuration...'

    def get_action_params(self, **kwargs):
        """
        Status method to get the command uri part
        """
        params = '&command={}&debug={}'.format(self.action, DEBUG)
        return params

    @staticmethod
    def add_args(subparsers):
        """
        Defines the command structure for power command
        """
        power_parser = subparsers.add_parser('status',
                                             help='Sub-command to work with '
                                                  'status of the cluster.')
        power_parser.set_defaults(func=Status)

    def execute_action(self, **kwargs):
        """
        Process the support_bundle response from the business layer
        """
        # pylint:disable=too-many-function-args
        try:
            response_data = super(Status, self).execute_action(**kwargs)
            response_str = self.get_human_readable_response(response_data)
        # pylint:disable=broad-except
        except Exception:
            response_str = 'An Internal error has occurred, unable to ' \
                           'complete command.'
        return response_str

    @staticmethod
    def get_human_readable_response(result):
        """
        Parse the json to read the human readable response
        """
        result = result and result[-1]
        response = 'An Internal error has occurred, unable to complete ' \
                   'command.'
        active_nodes = '\n\t'.join(result.get('active_nodes', []))
        inactive_nodes = '\n\t'.join(result.get('inactive_nodes', []))
        if active_nodes:
            response = 'Active Nodes:- \n\t{}'.format(active_nodes)
        if inactive_nodes:
            response = '{} \n Inactive Nodes:- \n\t{}'.format(
                response,
                inactive_nodes
            )
        return response
