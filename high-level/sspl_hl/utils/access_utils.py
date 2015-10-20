"""
This class decides which access object to use
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

import ConfigParser
# Local
from sspl_hl.utils.ldap_access import LdapAccess

AUTH_SECTION = 'Auth'
AUTH_METHOD = 'auth_method'
LDAP_AUTH = 'ldap'


class AccessUtils(object):
    # pylint: disable=too-few-public-methods
    """
    This will return access object depending upon the auth type mentioned
    in properties file
    """

    @staticmethod
    def get_access_object():
        """
        Returns access object depending upon the authentication method
        :return: An access object
        """
        config = ConfigParser.ConfigParser()
        config.read("/opt/plex/apps/sspl_hl/utils/auth.properties")
        auth_method = config.get(AUTH_SECTION, AUTH_METHOD)

        if auth_method == LDAP_AUTH:
            ldap_access_obj = LdapAccess()
            return ldap_access_obj
        else:
            raise Exception("Authentication method not supported")
