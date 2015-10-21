""" Unit tests for sspl_hl.providers.ldap.provider """


import unittest
from mock import MagicMock
from mock import patch
from sspl_hl.providers.ldap.provider import LdapProvider
from base_unit_test import BaseUnitTest


# pylint: disable=too-many-public-methods


class SsplHlProviderLdap(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.ldap.provider.LdapProvider object.
    """

    # pylint: disable=no-self-use
    @patch('ldap.initialize')
    def test_ldapadminshow_queries(self, mock_obj):
        """
            Ensure that the arguments passed to show
            command are taken by provider.
        """
        mocked_inst = mock_obj.return_value
        mocked_inst.search_s = MagicMock()
        self._query_provider(
            args={
                'command': 'user',
                'subcommand': 'show',
                'user': 'Victor@Clogeny'
            },
            provider=LdapProvider('LdapProvider', '')
            )
        self.assertTrue(mocked_inst.search_s.called)

    @patch('ldap.initialize')
    def test_ldapadminlist_queries(self, mock_obj_n):
        """
            Ensure list command will return all records in LDAP
        """
        mocked_inst_n = mock_obj_n.return_value
        mocked_inst_n.search_s = MagicMock()
        self._query_provider(
            args={
                'command': 'user',
                'subcommand': 'list',
                'user': 'all'
            },
            provider=LdapProvider('LdapProvider', '')
            )
        self.assertTrue(mocked_inst_n.search_s.called)

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.
        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'invalid_command', 'subcommand': 'show',
                        'user': 'Victor@Clogeny'}
        response_msg = "Error: Invalid command: 'invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         LdapProvider('LdapProvider', ''))

    def test_bad_subcommand(self):
        """ Ensure sending a bad subcommand results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'user', 'subcommand': 'invalid_subcommand',
                        'user': 'Victor@Clogeny'}

        response_msg = "Error: Invalid subcommand: 'invalid_subcommand'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         LdapProvider('LdapProvider', ''))

    def test_extra_ldap_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'user',
                        'subcommand': 'list',
                        'user': 'Victor@Clogeny',
                        'ext': 'up'}
        response_msg = "Error: Invalid request: Extra parameter 'ext' detected"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         LdapProvider('LdapProvider', ''))

    def test_missing_subcommand(self):
        """ Ensure sending query without subcommand results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'user'}
        response_msg = "Error: Invalid request: Missing subcommand"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         LdapProvider('LdapProvider', ''))

    def test_missing_user(self):
        """ Ensure sending query without user name results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'user',
                        'subcommand': 'show'}
        response_msg = "Error: Invalid request: Missing user"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         LdapProvider('LdapProvider', ''))

if __name__ == '__main__':
    unittest.main()
