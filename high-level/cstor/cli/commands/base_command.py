#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
File containing base class implementation for all the
sub commands supported by cstor
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

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
        url = 'http://{0}{1}data?{3}'.format(
            BL_HOST,
            self.get_provider_base_url(),
            self.get_action_params(**kwargs))
        response = urllib.urlopen(url=url)
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
