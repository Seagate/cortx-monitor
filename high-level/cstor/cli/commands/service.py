#!/usr/bin/python
# -*- coding: utf-8 -*-

""" File containing "service" sub command implementation
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
from cstor.cli.settings import DEBUG


class Service(BaseCommand):

    """ Service command implementation class
    """

    def __init__(self, parser):
        """ Initializes the service object with the
        arguments passed from CLI
        """

        super(Service, self).__init__()
        self.action = parser.action
        if 'service_name' in parser:
            self.resource = parser.service_name
        else:
            self.resource = None

        if 'node_spec' in parser:
            self.target = parser.node_spec
        else:
            self.target = None
        self.provider = 'service'

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for service command
        """
        parent_service_parser = argparse.ArgumentParser(add_help=False)

        parent_service_parser.add_argument('service_name',
                                           help='Service to operate on '
                                                'e.g. crond.service')
        parent_service_parser.add_argument('--node_spec',
                                           help='Optional parameter to '
                                                'indicate the Regex for'
                                                ' nodes that should be '
                                                'affected.')

        service_parser = subparsers.add_parser('service',
                                               help='Subcommand to work with '
                                                    'services on the cluster.')

        action_parser = service_parser.add_subparsers(dest='action',
                                                      help='Command to run.')
        action_parser.add_parser('start', parents=[parent_service_parser])
        action_parser.add_parser('stop', parents=[parent_service_parser])
        action_parser.add_parser('restart', parents=[parent_service_parser])
        action_parser.add_parser('enable', parents=[parent_service_parser])
        action_parser.add_parser('disable', parents=[parent_service_parser])
        action_parser.add_parser('list')

        service_parser.set_defaults(func=Service)

    def get_action_params(self, **kwargs):
        """ Service class specific implementation of the abstract method
        from base class
        Returns the list of action specific parameters to be sent
        in the request to data provider
        """

        params = 'serviceName={}&command={}&debug={}'.format(self.resource,
                                                             self.action,
                                                             DEBUG)
        return params
