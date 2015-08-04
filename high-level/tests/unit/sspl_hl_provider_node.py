""" Unit tests for sspl_hl.providers.service.provider """


import unittest

from sspl_hl.providers.node.provider import NodeProvider
from base_unit_test import BaseUnitTest


# pylint: disable=too-many-public-methods
class SsplHlProviderService(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.service.provider.NodeProvider object.
    """
    NODE_COMMAND = ['start',
                    'stop',
                    'restart']

    def test_node_queries(self):
        """ Ensures restarting,etc a service generates the proper json message.
        """
        for command in SsplHlProviderService.NODE_COMMAND:
            method_args = {'command': command,
                           'target': 'crond.service'}
            selection_args = {'command': command,
                              'target': 'crond.service'}
            # pylint: disable=protected-access
            self._test_entity_query(selection_args,
                                    NodeProvider._generate_node_request_msg,
                                    method_args,
                                    NodeProvider('node', ''))

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'invalid_command', 'target': 'crond'}
        response_msg = "Error: Invalid command: 'invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         NodeProvider('service', ''))

    def test_extra_service_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'restart',
                        'target': 'node1',
                        'ext': 'up'}
        response_msg = "Error: Invalid request: Extra parameter 'ext' detected"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         NodeProvider('node', ''))

    def test_missing_target(self):
        """ Ensure sending query without service name results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'restart'}
        response_msg = "Error: Invalid request: Missing target"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         NodeProvider('node', ''))

    def test_missing_command(self):
        """ Ensure sending query without command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'target': 'node'}
        response_msg = "Error: Invalid request: Missing command"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         NodeProvider('node', ''))


if __name__ == '__main__':
    unittest.main()
