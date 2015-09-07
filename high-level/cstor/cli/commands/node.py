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

# Third Party
import json
import time
import argparse

# Import Local Modules
from cstor.cli.commands.base_command import BaseCommand
from cstor.cli.settings import DEBUG
from cstor.cli.errors import InvalidResponse


RETRY_CNT = 5
RETRY_SLEEP_SEC = 5


class Node(BaseCommand):

    """ Node command implementation class
    """
    STATUS_RESPONSE_KEY = "statusResponse"
    ENTITY_ID_KEY = "entityId"

    def __init__(self, parser):
        """ Initializes the node object with the
        arguments passed from CLI
        """

        super(Node, self).__init__()

        if 'action' in parser:
            self.action = parser.action
        else:
            self.action = None
        if 'node_spec' in parser:
            self.target = parser.node_spec
        else:
            self.target = None
        self.provider = 'node'

    def execute_action(self):
        """ Function to execute the action by sending
        request to data provider in business logic server.
        Overriding will have the handling for status command.
        """
        response = super(Node, self).execute_action()
        if self.action == 'status':
            return Node._handle_status_request(response)
        elif self.action == 'list':
            result = Node._handle_status_request(response)
            if result:
                return Node._parse_status_response(result)
        else:
            return response

    @staticmethod
    def _parse_status_response(response):
        items = json.loads(response[0])[Node.STATUS_RESPONSE_KEY]
        return [item[Node.ENTITY_ID_KEY] for item in items]

    @staticmethod
    def add_args(subparsers):
        """ Defines the command structure for node command.
        """
        parent_node_parser = argparse.ArgumentParser(add_help=False)

        parent_node_parser.add_argument('--node_spec',
                                        default=None,
                                        help='Optional parameter to indicate'
                                             ' the Regex for nodes that '
                                             'should be affected.')

        node_parser = subparsers.add_parser('node',
                                            help='Sub-command to work with '
                                            'node of the cluster.')

        action_parser = node_parser.add_subparsers(dest='action',
                                                   help='Command to run.')
        action_parser.add_parser('start', parents=[parent_node_parser])
        action_parser.add_parser('stop', parents=[parent_node_parser])
        action_parser.add_parser('enable', parents=[parent_node_parser])
        action_parser.add_parser('disable', parents=[parent_node_parser])
        action_parser.add_parser('status', parents=[parent_node_parser])
        action_parser.add_parser('list')

        node_parser.set_defaults(func=Node)

    def get_action_params(self, **kwargs):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """
        params = '&command={}&target={}&debug={}'.format(self.action,
                                                         self.target,
                                                         DEBUG)
        return params

    @staticmethod
    def _is_response_empty(response):
        """
        Check if response contains at least one element in return list.
        @param response: message from response provider.
        @type response: str.

        @return: response message is empty or not.
        @rtype: bool
        """
        try:
            resp_dict = json.loads(response)
            if not resp_dict:
                return True
            else:
                return False
        except ValueError:
            raise ValueError("Could not load the response in json object")

    @staticmethod
    def _handle_status_request(status_response):
        """
        Node status response handler for node status request.
        1. Get the messageId from Node response status.
        2. Query Response provider with messageId to get the
           status command response.
        3. If response is empty retry till defined RETRY_CNT.
        4. Pause for RETRY_SLEEP_SEC in between retries.

        @param status_response: Node status command response
        @type status_response: str
        """

        msg_id = Node._get_message_id(status_response)
        from cstor.cli.commands.responder import Responder
        res_request = Responder()
        for retry in range(1, RETRY_CNT):
            response = res_request.execute_action(message_id=msg_id)
            if Node._is_response_empty(response):
                print "Retry:{} for message_id:{}".format(retry, msg_id)
                time.sleep(RETRY_SLEEP_SEC)
            else:
                break
        return json.loads(response)

    @staticmethod
    def _get_message_id(status_response):
        """
            Extract the message id from the node status response
        """
        try:
            status_response = json.loads(status_response)
        except:
            raise InvalidResponse(desc="Invalid node status response")
        if 'message' in status_response[0] and \
           'messageId' in status_response[0]['message']:
            return status_response[0]['message']['messageId']
        else:
            raise InvalidResponse(desc="Invalid node status response. "
                                       "Error occurred while parsing "
                                       "the response message")
