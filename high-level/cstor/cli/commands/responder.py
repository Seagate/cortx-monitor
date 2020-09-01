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


""" File containing "service" sub command implementation
"""

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
