#!/usr/bin/python
# -*- coding: utf-8 -*-

""" File containing base class implementation for all the
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

# Import System Modules

import urllib
import abc

# Import local Modules

from cstor.cli.settings import BL_HOST


class BaseCommand(object):

    """ This is a Abstract class, defined as a base class for
    all the different types of sub-commands supported by Castor cli
    """

    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """ Init method of base class.
        """
        pass

    def execute_action(self):
        """ Function to execute the action by sending
        request to data provider in business logic server
        """

        url = 'http://%s%sdata?%s' % (
            BL_HOST,
            self.get_provider_base_url(),
            self.get_action_params())

        urllib.urlopen(url=url)

    @abc.abstractmethod
    def get_provider_base_url(self):
        """ Abstract method to get the base url for
        the resource specific data provider
        """

        raise NotImplementedError

    @abc.abstractmethod
    def get_action_params(self):
        """ Abstract method to get the action parameters
        to be send in the request to data provider
        """

        raise NotImplementedError
