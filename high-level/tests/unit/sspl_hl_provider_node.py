""" Unit tests for sspl_hl.providers.service.provider """


import unittest
import mock
import json

from sspl_hl.providers.node.provider import NodeProvider
from base_unit_test import BaseUnitTest
from sspl_hl.utils.message_utils import StatusRequest

STATUS_REQUEST_KEY = StatusRequest.STATUS_REQUEST_KEY
ENTITY_TYPE_KEY = StatusRequest.ENTITY_TYPE_KEY
ENTITY_FILTER_KEY = StatusRequest.ENTITY_FILTER_KEY


# pylint: disable=too-many-public-methods
class SsplHlProviderService(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.service.provider.NodeProvider object.
    """
    NODE_COMMAND = ['start',
                    'stop',
                    'enable',
                    'disable',
                    'status',
                    'list']
    INTERNAL_COMMAND = {'start': 'poweron',
                        'stop': 'poweroff'}

    def test_node_message_structure(self):
        """ Ensures node poweron, stop, status, etc
            generates a proper json request message.
        """
        for command in SsplHlProviderService.NODE_COMMAND:

            selection_args = {'command': command,
                              'target': "node*",
                              'debug': False}

            with mock.patch('uuid.uuid4', return_value='uuid_goes_here'), \
                    mock.patch('pika.BlockingConnection') as patch:
                # pylint: enable=protected-access
                self._query_provider(args=selection_args,
                                     provider=NodeProvider('node', ''))

            args, kwargs = patch().channel().basic_publish.call_args
            self.assertEquals(args, ())
            body = json.loads(kwargs["body"])
            if command in ['status', 'list']:
                entity_type = \
                    body["message"][STATUS_REQUEST_KEY][ENTITY_TYPE_KEY]
                entity_filter = \
                    body["message"][STATUS_REQUEST_KEY][ENTITY_FILTER_KEY]
                self.assertEqual(entity_type, "node")
                if command == 'status':
                    self.assertRegexpMatches(entity_filter,
                                             "n*",
                                             "Not a valid Node Name!")
                else:
                    self.assertEquals(entity_filter, ".*",
                                      "List should have target as "
                                      "a regex to match all nodes!")
            else:
                nodes = body["message"]["nodeStatusChangeRequest"]["nodes"]
                action = \
                    body["message"]["nodeStatusChangeRequest"]["command"]
                command = self.INTERNAL_COMMAND.get(command, command)
                self.assertEquals(action, command)
                self.assertEquals(nodes, "node*")

    def test_node_queries(self):
        """ Ensures start, stop, etc a node publishes
            proper messages to rabbit mq.
        """
        for command in SsplHlProviderService.NODE_COMMAND:
            method_args = {'command': command,
                           'target': 'node*'}
            selection_args = {'command': command,
                              'target': 'node*',
                              'debug': False}
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
        command_args = {'command': 'invalid_command', 'target': 'node*',
                        'debug': False}
        response_msg = "Error: Invalid command: 'invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         NodeProvider('node', ''))

    def test_extra_service_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'start',
                        'target': 'node*',
                        'debug': False,
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
        command_args = {'command': 'start'}
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
        command_args = {'target': 'node*'}
        response_msg = "Error: Invalid request: Missing command"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         NodeProvider('node', ''))


if __name__ == '__main__':
    unittest.main()
