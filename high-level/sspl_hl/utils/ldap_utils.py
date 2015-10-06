#!/usr/bin/python
# -*- coding: utf-8 -*-

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

"""
This module will handle Ldap show and list queries.
"""

# Third party
import ldap


class LdapUtils(object):
    """
        Return the individual record in case of 'show' command and
        display list of all records in Ldap directory
        as a result of 'list' command.
    """
    def __init__(self):
        self.ld_init = ldap.initialize('ldap://localhost')

    def showuser(self, user_name, dc_base, dc_root):
        """
        Return the details of person specified in target
        """
        try:
            # searching doesn't require a bind in LDAP V3.
            # If you're using LDAP v2, set the next line appropriately
            # and do a bind as shown in the above example.
            # you can also set this to ldap.VERSION2
            # if you're using a v2 directory
            # you should  set the next option to ldap.
            # VERSION2 if you're using a v2 directory
            self.ld_init.protocol_version = ldap.VERSION3
        except ldap.LDAPError, erro:
            print erro
            # handle error however you like
        # specify search requirements and directory
        list_rdn = user_name.split('@', 1)
        base_dn = 'ou={0},dc={1},dc={2}'.format(list_rdn[1], dc_base, dc_root)
        search_scope = ldap.SCOPE_SUBTREE
        # retrieve all attributes - again adjust to your needs
        search_filter = 'cn={0}'.format(list_rdn[0])
        res = []
        try:
            res = self.ld_init.search_s(
                base_dn, search_scope, search_filter, None)
        except ldap.NO_SUCH_OBJECT:
            pass
        return res

    def showlist(self, dc_base, dc_root):
        """
        Return list of records in ldap directory
        """

        # first you must open a connection to the server
        try:
            self.ld_init.protocol_version = ldap.VERSION3
        except ldap.LDAPError, erro:
            print erro
            # handle error however you like
        # specify search requirements and directory
        base_dn = "dc={0},dc={1}".format(dc_base, dc_root)
        search_scope = ldap.SCOPE_SUBTREE
        # retrieve all attributes - again adjust to your needs
        search_filter = "cn=*"
        res = self.ld_init.search_s(base_dn, search_scope, search_filter, None)
        return res
