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


class Responder(BaseCommand):

    """ Responder command implementation class
    """

    def __init__(self):
        """ Initializes the service object with the
        arguments passed from CLI
        """
        super(Responder, self).__init__()
        self.provider = 'response'

    def get_action_params(self, **kwargs):
        """
            Responder class specific implementation of the abstract method
            from base class
            Returns the list of action specific parameters to be sent
            in the request to data provider
        """

        params = 'messageId={}'.format(kwargs.get('message_id', None))
        return params
