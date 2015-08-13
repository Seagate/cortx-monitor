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

# Import Local Modules

from cstor.cli.commands.base_command import BaseCommand


class Service(BaseCommand):

    """ Service command implementation class
    """

    def __init__(self, parser):
        """ Initializes the service object with the
        arguments passed from CLI
        """

        super(Service, self).__init__()
        self.action = parser.action
        self.resource = parser.service_name
        self.target = parser.node_spec
        self.provider = 'service'

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for service command
        """

        service_parser = subparsers.add_parser('service',
                                               help='Subcommand to work with '
                                               'services on the cluster.')
        service_parser.add_argument('action', help='Command to run.', choices=[
            'start',
            'stop',
            'restart',
            'enable',
            'disable',
            'status',
            'list'
            ])
        service_parser.add_argument('service_name',
                                    help='Service to operate on.  '
                                    'e.g. crond.service')
        service_parser.set_defaults(func=Service)
        service_parser.add_argument('--node_spec',
                                    help='Optional parameter to indicate which'
                                    ' nodes should be affected.')

    def get_action_params(self, **kwargs):
        """ Service class specific implementation of the abstract method
        from base class
        Returns the list of action specific parameters to be sent
        in the request to data provider
        """

        params = 'serviceName={}&command={}'.format(self.resource, self.action)
        return params
