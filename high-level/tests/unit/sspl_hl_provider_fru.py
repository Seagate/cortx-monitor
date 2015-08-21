""" Unit tests for sspl_hl.providers.service.provider """


import unittest

from sspl_hl.providers.fru.provider import FRUProvider
from base_unit_test import BaseUnitTest


# pylint: disable=too-many-public-methods
class SsplHlProviderFRU(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.fru.provider.FRUProvider object.
    """
    FRU_COMMAND = ['status', 'list']

    def test_fru_queries(self):
        """ Ensures fru,etc a service generates the proper json message.
        """
        for command in SsplHlProviderFRU.FRU_COMMAND:
            fru_method_args = {'fru_command': command, 'fru_target': 'node*'}
            fru_selection_args = {'command': command,
                                  'target': 'node*',
                                  'debug': False}
            # pylint: disable=protected-access
            self._test_entity_query(fru_selection_args,
                                    FRUProvider._generate_fru_request_msg,
                                    fru_method_args,
                                    FRUProvider('fru', ''))

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'fru_invalid_command',
                        'target': 'node*',
                        'debug': False}
        response_msg = "Error: Invalid command: 'fru_invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         FRUProvider('fru', ''))

    def test_extra_service_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        fru_command_args = {'command': 'status',
                            'target': 'node*',
                            'debug': False,
                            'ext': 'up'}
        response_msg = "Error: Invalid request: Extra parameter 'ext' detected"
        self._test_args_validation_cases(fru_command_args,
                                         response_msg,
                                         FRUProvider('fru', ''))

    def test_missing_target(self):
        """ Ensure sending query without service name results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'status'}
        response_msg = "Error: Invalid request: Missing target"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         FRUProvider('fru', ''))

    def test_missing_command(self):
        """ Ensure sending query without command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        fru_command_args = {'target': 'node*'}
        response_msg = "Error: Invalid request: Missing command"
        self._test_args_validation_cases(fru_command_args,
                                         response_msg,
                                         FRUProvider('fru', ''))


if __name__ == '__main__':
    unittest.main()
