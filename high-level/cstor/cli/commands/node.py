#!/usr/bin/python
# -*- coding: utf-8 -*-

""" File containing "node" sub command implementation
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
from cstor.cli.settings import DEBUG
import json


class Node(BaseCommand):

    """ Node command implementation class
    """

    def __init__(self, parser):
        """ Initializes the node object with the
        arguments passed from CLI
        """

        super(Node, self).__init__()
        self.action = parser.command
        self.target = parser.node_spec
        self.provider = 'node'

    def execute_action(self):
        """ Function to execute the action by sending
        request to data provider in business logic server.
        Overridding will have the handling for status command.
        """
        response = super(Node, self).execute_action()
        if self.action == 'status':
            return Node._handle_status_request(response)
        else:
            return response

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for node command
        """

        node_parser = subparsers.add_parser('node',
                                            help='Sub-command to work with '
                                            'node of the cluster.')
        node_parser.add_argument('command', help='Command to run.',
                                 choices=['start', 'stop',
                                          'restart', 'status'])
        node_parser.add_argument('node_spec', help='Regex for the node names')
        node_parser.set_defaults(func=Node)

    def get_action_params(self):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """
        params = '&command={}&target={}&debug={}'.format(self.action,
                                                         self.target,
                                                         DEBUG)
        return params

    @staticmethod
    def _handle_status_request(status_response):
        """
            Handle the status response handling for parsing the request_id
            and query provider for the response.
        """

        message_id = Node._get_message_id(status_response)
        # url = 'http://{}/response/messageId={}'.format(BL_HOST,
        #  message_id)
        try:
            response = '{"Response": "Dummy status response received!", ' \
                       '"messageID": "%s"}' % message_id
            # response = urllib.urlopen(url=url).read()
            return json.dumps(json.loads(response), indent=2)
        except ValueError:
            raise ValueError("Could not load the response in json object")

    @staticmethod
    def _get_message_id(status_response):
        """
            Extract the message id from the node status response
        """
        try:
            status_response = json.loads(status_response)
        except ValueError:
            raise ValueError("Invalid node status resonse")
        if 'message' in status_response[0] and \
           'messageId' in status_response[0]['message']:
            return status_response[0]['message']['messageId']
        else:
            raise ValueError("Invalid node status resonse")
