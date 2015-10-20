"""Interface for methods used for authentication, authorization
and access control"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

import abc


class IBaseAccess(object):
    """Interface for authentication, authorization and access control"""
    # pylint: disable=abstract-class-little-used,R0922

    @abc.abstractmethod
    def authenticate_user(self):
        """
        Authenticates the given user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def authorize_user(self):
        """
        Authorizes the given user
        """
        raise NotImplementedError

    @abc.abstractmethod
    def login_user(self, username, password):
        """
        Login with given username and password
        """
        raise NotImplementedError
