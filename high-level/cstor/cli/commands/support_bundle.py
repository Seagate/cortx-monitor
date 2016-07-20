#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
File containing "bundle" command implementation
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

from cstor.cli.commands.base_command import BaseCommand
import cstor.cli.errors as errors


class SupportBundle(BaseCommand):

    """ support_bundle command implementation class
    """

    def __init__(self, parser):
        """ Initializes the bundle object with the
        arguments passed from CLI
        """

        super(SupportBundle, self).__init__()
        self.command = parser.command
        self.provider = "bundle"

    @staticmethod
    def add_args(subparsers):
        """ defines the command structure for bundle command
        """

        sb_parser = subparsers.add_parser('bundle',
                                          help='Sub-command \
        to work on support related operations')

        sb_parser.add_argument('command', help='command \
            to run', choices=['create', 'list'])

        sb_parser.set_defaults(func=SupportBundle)

    def get_action_params(self, **kwargs):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """
        params = 'command={}'.format(self.command)
        return params

    def execute_action(self, **kwargs):
        """
        Process the support_bundle response from the business layer
        """
        # pylint:disable=too-many-function-args
        try:
            response = super(SupportBundle, self).execute_action(**kwargs)
            response = self.get_human_readable_response(response)

        # pylint:disable=broad-except
        except Exception:
            raise errors.InternalError()
        return response

    @staticmethod
    def get_human_readable_response(response):
        """
        Parse the json to read the human readable response
        """
        response = response and response[0]
        message = response.get('message')
        for key in message.keys():
            if key == 'bundle_name':
                return SupportBundle.get_create_bundle_response(message)
            elif key == 'bundle_info':
                return SupportBundle.get_bundle_list_response(message)

    @staticmethod
    def get_bundle_list_response(message):
        """
        Format the bundle list response
        """
        count = 0
        response = ''
        bundle_info = message.get('bundle_info')
        for tar_file in bundle_info.get('completed'):
            count += 1
            response = '{}\n {}'.format(response, tar_file)
        response = 'Bundles are available at {}\n\n' \
                   'Total bundles available: {} {}'.\
            format(message.get('bundle_path'),
                   count, response)
        in_progress_bundle = ''
        count = 0
        for in_progress in bundle_info.get('in_progress'):
            count += 1
            in_progress_bundle = '{}\n {}'.format(
                in_progress_bundle,
                in_progress
            )
        response = '{}\n\nBundling in progress: {}{}'.format(
            response,
            count,
            in_progress_bundle
        )
        return response

    @staticmethod
    def get_create_bundle_response(message):
        """
        Format the bundle create response
        """
        name = message.get('bundle_name', None)
        response = 'Bundle creation has been initiated, File: {} ' \
                   '\nUse the bundle \'list\' command to monitor the ' \
                   'progress.'.format(name)

        return response


# resp = {'username': 'ignored_for_now', 'message': {'bundle_path':
# '/var/lib/support_bundles', 'bundle_info': {'in_progress':
# ['2016-07-13_04-52-51', '2016-07-13_04-52-52', '2016-07-13_04-52-56'],
# 'completed': ['2016-07-13_04-52-561.tar', '2016-07-13_04-52-533.tar',
# '2016-07-13_04-152-56.tar']}, 'messageId':
# '82fcc575-7fda-4738-9520-4e1091a09634'},
# 'time': '2016-07-19T09:10:10.323633+00:00', 'expires': 3600,
# 'signature': 'None'}
# print SupportBundle.get_bundle_list_response(resp['message'])
