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

# Import Local Modules
from cstor.cli.commands.base_command import BaseCommand
from cstor.cli.settings import DEBUG

FRU_RETRY_CNT = 5
FRU_RETRY_SLEEP_SEC = 5


class FieldReplaceableUnit(BaseCommand):

    """ FRU command implementation class
    """

    def __init__(self, parser):
        """ Initializes the fru object with the
        arguments passed from CLI
        """

        super(FieldReplaceableUnit, self).__init__()
        self.action = parser.command
        self.target = parser.hwtype
        self.provider = 'fru'

    def execute_action(self):
        """ Function to execute the action by sending
        request to data provider in business logic server.
        Overridding will have the handling for status command.
        """
        response = super(FieldReplaceableUnit, self).execute_action()
        if self.action == 'status':

            response = FieldReplaceableUnit._handle_status_request(response)
        elif self.action == 'list':
            response = FieldReplaceableUnit._handle_list_request(response)
        return json.dumps(response, indent=2)

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for fru command
        """

        fru_parser = subparsers.add_parser(
            'fru',
            help='Sub-command to work with fru of the cluster.'
        )
        fru_parser.add_argument(
            'command',
            help='Command to run.',
            choices=['list', 'status'],
        )
        fru_parser.add_argument(
            'hwtype',
            help='Regex for the node names',
            # NOTE: The below options are still under implementation
            #       discussion and kept here for tracking
            # default='node',
            # choices=['node', 'disk']
        )
        fru_parser.set_defaults(func=FieldReplaceableUnit)

    def get_action_params(self):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """
        fru_params = '&command={}&target={}&debug={}'.format(self.action,
                                                             self.target,
                                                             DEBUG)
        return fru_params

    @staticmethod
    def _is_response_empty(fru_response):
        """
        Check if response contains at least one element in return list.
        @param response: message from response provider.
        @type response: str.

        @return: response message is empty or not.
        """
        try:
            fru_resp_dict = json.loads(fru_response)
        except ValueError:
            raise ValueError("Could not load the response in json object")
        return bool(fru_resp_dict)

    @staticmethod
    def _handle_status_request(status_response):
        """
        FRU status response handler for fru status request.
        1. Get the messageId from FRU response status.
        2. Query Response provider with messageId to get the
           status command response.
        3. If response is empty retry till defined RETRY_CNT
        4. Pause for RETRY_SLEEP_SEC in between retries.

        @param status_response: fru status command response
        @type status_response: str
        """

        fru_msg_id = FieldReplaceableUnit._get_message_id(status_response)
        from cstor.cli.commands.responder import Responder
        fru_res_request = Responder()
        for retry in range(1, FRU_RETRY_CNT):
            fru_response = fru_res_request.execute_action(
                message_id=fru_msg_id)
            if FieldReplaceableUnit._is_response_empty(fru_response):
                print "Retry:{} for message_id:{}".format(retry, fru_msg_id)
                time.sleep(FRU_RETRY_SLEEP_SEC)
            else:
                break
        # NOTE: The below snippet is dummy as fru is not
        # covered by halon
        if not fru_response or fru_response == '[]':
            fru_response = json.dumps({
                "message": {
                    "fan": "ok",
                    "sati": "not ok",
                    "ddic": "ok",
                    "bezel": "not ok"
                }
            })

        return json.loads(fru_response)

    @staticmethod
    def _handle_list_request(list_response):
        """
        FRU list response handler for fru list request.
        1. Get the messageId from FRU response list.
        2. Query Response provider with messageId to get the
           status command response.
        3. If response is empty retry till defined RETRY_CNT
        4. Pause for RETRY_SLEEP_SEC in between retries.

        @param list_response: fru list command response
        @type list_response: str
        """

        fru_msg_id = FieldReplaceableUnit._get_message_id(list_response)
        from cstor.cli.commands.responder import Responder
        fru_res_request = Responder()
        for retry in range(1, FRU_RETRY_CNT):
            fru_response = fru_res_request.execute_action(
                message_id=fru_msg_id)
            if FieldReplaceableUnit._is_response_empty(fru_response):
                print "Retry:{} for message_id:{}".format(retry, fru_msg_id)
                time.sleep(FRU_RETRY_SLEEP_SEC)
            else:
                break
        # NOTE: The below snippet is dummy as fru is not
        # covered by halon
        if not fru_response or fru_response == "[]":
            fru_response = json.dumps({"message": ["powerfan",
                                                   "sas", "infiniband"]},
                                      indent=2)
        return json.loads(fru_response)

    @staticmethod
    def _get_message_id(fru_status_response):
        """
            Extract the message id from the fru status response
        """
        try:
            fru_status_response = json.loads(fru_status_response)
        except ValueError:
            raise ValueError("Invalid fru status resonse")
        if not fru_status_response or fru_status_response == '[]':
            raise RuntimeError('fru status response invalid')
        elif 'message' in fru_status_response[0] and \
                'messageId' in fru_status_response[0]['message']:
            return fru_status_response[0]['message']['messageId']
        else:
            raise ValueError("Invalid fru status resonse")
