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


"""File containing "status" sub command implementation
"""

# Third Party
# Import Local Modules
import json
from cstor.cli.commands.base_command import BaseCommand
from cstor.cli.settings import DEBUG
import cstor.cli.errors as errors


class Status(BaseCommand):
    """
    Power command implementation class
    """
    STATUS_RESPONSE_KEY = "statusResponse"
    ENTITY_ID_KEY = "entityId"
    STATUS_KEY = "status"

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

    @staticmethod
    def is_json(myjson):
        """ Verify for JSON structure
        """
        # pylint: disable=unused-variable
        try:
            json_object = json.loads(myjson)
        # pylint: disable=invalid-name
        except ValueError, e:
            return False
        return True

    def get_action_params(self, **kwargs):
        """
        Status method to get the command uri part
        """
        params = '&command={}&debug={}'.format(self.action, DEBUG)
        return params

    @staticmethod
    def _parse_status_response(response):
        item = json.loads(response)[Status.STATUS_RESPONSE_KEY][0]
        return item.get(Status.STATUS_KEY, '')

    @staticmethod
    def add_args(subparsers):
        """
        Defines the command structure for power command
        """
        power_parser = subparsers.add_parser('status',
                                             help='Sub-command to work with '
                                                  'status of the nodes.')
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
            raise errors.InternalError()
        return response_str

    @staticmethod
    def get_human_readable_response(result):
        """
        Parse the json to read the human readable response
        """
        try:
            result = result and result[-1]
            power_resp = result.get('power_status', {})
            sem_resp = result.get('sem_status', '')
            file_status_resp = result.get('file_system_status', None)

            active_nodes = power_resp.get('active_nodes', [])
            inactive_nodes = power_resp.get('inactive_nodes', [])
            pwr_response = ''
            if active_nodes:
                active_nodes = '\n\t'.join(active_nodes)
                pwr_response = 'Active Nodes:- \n\t{}'.format(active_nodes)
            if inactive_nodes:
                inactive_nodes = '\n\t'.join(inactive_nodes)
                pwr_response = '{} \nInactive Nodes:- \n\t{}'.format(
                    pwr_response,
                    inactive_nodes
                )
            file_resp = None
            response = ''
            if file_status_resp:
                if file_status_resp[0]:
                    file_resp = file_status_resp[0]
                    if Status.is_json(file_resp):
                        file_resp = Status._parse_status_response(file_resp)
                        response = 'Filesystem status: {} \n\n'.format(
                            file_resp)
                    else:
                        response = 'Filesystem status: {} \n\n'.format(
                            file_resp)
            else:
                response = 'Filesystem status: No response \n\n'

            response += sem_resp
            response += '\n\n'
            response += pwr_response
            return response
        # pylint:disable=broad-except
        except Exception:
            raise errors.InternalError()
