"""This class is ldap specific implementation for authentication,
authorization and access control"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

import ldap
from sspl_hl.utils.ibase_access import IBaseAccess

DC_BASE = "seagate"
DC_ROOT = "com"


class LdapAccess(IBaseAccess):
    """
    Ldap specific implementation for authentication, authorization
    and access control
    """

    def __init__(self):
        self.ld_init = ldap.initialize('ldap://localhost')

    # pylint: disable=fixme
    def authenticate_user(self):
        # TODO: ldap implementation for authentication
        return True

    def authorize_user(self):
        # TODO: ldap implementation for authorization
        return True

    def login_user(self, username, password):
        """
        Validates whether user is valid or not
        """
        try:
            self.ld_init.protocol_version = ldap.VERSION3
        except ldap.LDAPError, error:
            print error

        # specify search requirements and directory
        list_rdn = username.split('@', 1)
        distinguished_name = 'cn={0},dc={1},dc={2}'.\
            format(list_rdn[0], DC_BASE, DC_ROOT)
        return_message = ""
        try:
            self.ld_init.bind_s(distinguished_name, password)
            return_message = "Login Successful"
        except ldap.INVALID_CREDENTIALS:
            print "Your username or password is incorrect."
            return_message = "Incorrect username and/or password. " \
                             "Login Failed."
        except ldap.LDAPError, error:
            if error.message and 'desc' in error.message:
                print error.message['desc']
            else:
                print error

            return_message = "Login Failed"

        return return_message

    # pylint: enable=fixme
