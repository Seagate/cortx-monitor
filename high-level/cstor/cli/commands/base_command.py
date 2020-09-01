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


"""
File containing base class implementation for all the
sub commands supported by cstor
"""

import urllib
import abc
import json
import cstor.cli.errors as errors
from cstor.cli.settings import BL_HOST, BL_SERVER_BASE_URL


class BaseCommand(object):
    """
    This is a Abstract class, defined as a base class for
    all the different types of sub-commands supported by Castor cli
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """
        Init method of base class.
        """
        self.provider = None

    def execute_action(self, **kwargs):
        """
        Function to execute the action by sending
        request to data provider in business logic server
        """
        # pylint:disable=too-many-function-args
        url = 'http://{0}{1}data?{2}'.format(
            BL_HOST,
            self.get_provider_base_url(),
            self.get_action_params(**kwargs))
        try:
            response = urllib.urlopen(url=url)
        except KeyboardInterrupt:
            raise errors.CommandTerminated()
        if response.getcode() == 200:
            data = response.read()
            try:
                return json.loads(data)
            except ValueError:
                raise errors.InvalidResponse()
        else:
            raise errors.InternalError()

    def get_provider_base_url(self):
        """
        Abstract method to get the base url for
        the resource specific data provider
        """
        registry_url = '{}registry/providers'.format(BL_SERVER_BASE_URL)
        providers = json.loads(urllib.urlopen(url=registry_url).read())
        try:
            return next(provider for provider in providers
                        if provider['application'] == 'sspl_hl' and
                        provider['name'] == self.provider)['uri']
        except StopIteration:
            raise RuntimeError('Unable to find the provider "{}" on {}'
                               .format(self.provider, BL_HOST))

    @abc.abstractmethod
    def get_action_params(self, **kwargs):
        """
        Abstract method to get the action parameters
        to be send in the request to data provider
        """

        raise NotImplementedError
