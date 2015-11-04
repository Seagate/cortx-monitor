""" Unit tests for sspl_hl.providers.access.provider """


import unittest
from mock import MagicMock
from mock import patch
from sspl_hl.providers.access.provider import AccessProvider
from base_unit_test import BaseUnitTest


# pylint: disable=too-many-public-methods


class SsplHlProviderLdap(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.ldap.provider.AccessProvider object.
    """

    # pylint: disable=no-self-use
    @patch('ldap.initialize')
    def test_access_queries(self, mock_obj):
        """
            Ensure that the arguments passed to login
            command are taken by provider.
        """
        mocked_inst = mock_obj.return_value
        mocked_inst.bind_s = MagicMock()
        self._query_provider(
            args={'username': 'Howard@Cstor', 'password': 'seagate'},
            provider=AccessProvider('AccessProvider', '')
            )
        self.assertTrue(mocked_inst.bind_s.called)

    def test_bad_username(self):
        """ Ensure sending a bad command results in an http error code.
        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'user': 'Howard@Cstor', 'password': 'seagate'}
        response_msg = "Error: Invalid request: Missing param username"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         AccessProvider('AccessProvider', ''))

    def test_bad_password(self):
        """ Ensure sending a bad subcommand results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'username': 'Howard@Cstor', 'pass': 'seagate'}

        response_msg = "Error: Invalid request: Missing param password"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         AccessProvider('AccessProvider', ''))

    def test_extra_access_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'username': 'Howard@Cstor',
                        'password': 'seagate',
                        'ext': 'up'}
        response_msg = "Error: Invalid request: Extra param 'ext' detected"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         AccessProvider('AccessProvider', ''))

    def test_missing_password(self):
        """ Ensure sending query without subcommand results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'username': 'Howard@Cstor'}
        response_msg = "Error: Invalid request: Missing param password"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         AccessProvider('AccessProvider', ''))

    def test_missing_username(self):
        """ Ensure sending query without user name results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'password': 'seagate'}
        response_msg = "Error: Invalid request: Missing param username"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         AccessProvider('AccessProvider', ''))

if __name__ == '__main__':
    unittest.main()
