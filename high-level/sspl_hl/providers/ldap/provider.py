"""
PLEX data provider.
"""
# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2014 - 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.

# Third party
from twisted.internet import reactor
# Local
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.ldap_utils import LdapUtils


class LdapProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
        Handler of LDAP directory operations such as
        Showing details of individual record and listing all records
        under seagate.com domain
    """

    def __init__(self, name, description):
        super(LdapProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command', 'subcommand', 'user']
        self.valid_commands = ['user', 'group']
        self.valid_subcommands = ['show', 'list']
        self.no_of_arguments = 3

    def _query(self, selection_args, responder):
        """
        Handler of LDAP directory operations such as
        Shows details of individual record or lists all records in LDAP.
        @param selection_args:  A dictionary that must contain
                                'command','subcommand' and 'user'.
        @param description:     The command should be 'user' or 'group'
                                The'subcommand' should be 'show' or 'list'.
                                The 'user' would be
                                the name of the person.
        @return:                This method will return
                                a record as per given query
        @rtype:                 JSON
        """
        result = super(LdapProvider, self)._query(selection_args, responder)
        message = None
        if result:
            reactor.callFromThread(responder.reply_exception, result)
            return
        else:
            util_ldap = LdapUtils()
            dc_base = "seagate"
            dc_root = "com"
            if selection_args['subcommand'] == 'show':
                message = util_ldap.showuser(selection_args['user'],
                                             dc_base, dc_root)
                if not message:
                    message = "User not found"
            elif selection_args['subcommand'] == 'list':
                message = util_ldap.showlist(dc_base, dc_root)
        reactor.callFromThread(responder.reply, data=[message])
        return

# pylint: disable=invalid-name
provider = LdapProvider("ldap", "Ldap Management Provider")
# pylint: enable=invalid-name
