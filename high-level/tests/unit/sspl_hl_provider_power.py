""" Unit tests for sspl_hl.providers.service.provider """
import unittest
import mock
from sspl_hl.providers.power.provider import PowerProvider
from base_unit_test import BaseUnitTest
from plex.core.provider.data_store_provider import ProviderQueryRequest
from plex.util.shell_command import ShellCommand


# pylint: disable=too-many-public-methods
class SsplHlProviderPower(BaseUnitTest):
    """
    Test methods of the
    sspl_hl.providers.service.provider.NodeProvider object.
    """
    POWER_COMMAND = ['on',
                     'off']

    INTERNAL_COMMAND = {'on': 'poweron',
                        'off': 'poweroff'}

    @staticmethod
    def _get_mock_request_object(command):
        """
        Return the mock request object.
        """
        request_mock = mock.MagicMock(spec=ProviderQueryRequest)
        request_mock.selection_args = {'command': command}
        return request_mock

    def setUp(self):
        super(SsplHlProviderPower, self).setUp()
        self.mocked_cluster_node_information = mock.MagicMock()
        self.mocked_cluster_node_information.get_cluster_state_info = mock.\
            MagicMock()

    def test_power_for_cluster_up(self):
        """
        Gives appropriate call depending on cluster state
        """

        request_mock = mock.MagicMock()
        self.mocked_cluster_node_information.get_cluster_state_info.\
            return_value = (
                "up", {"key1": [], "key2": []})
        command_args = {'command': 'on'}
        request_mock.selection_args = command_args
        power_provider = PowerProvider('bundle', 'test_bundle',
                                       self.mocked_cluster_node_information)
        power_provider.render_query(request_mock)
        self.assertEqual(request_mock.reply.call_count, 1)

    def test_power_for_cluster_down(self):
        """
        Gives appropriate call depending on cluster state
        """
        request_mock = mock.MagicMock()
        self.mocked_cluster_node_information.get_cluster_state_info.\
            return_value = (
                "down", {"key1": [], "key2": []})
        command_args = {'command': 'off'}
        request_mock.selection_args = command_args
        power_provider = PowerProvider('bundle', 'test_bundle',
                                       self.mocked_cluster_node_information)
        power_provider.render_query(request_mock)
        self.assertEqual(request_mock.reply.call_count, 1)

    def test_power_queries_cmd_called(self):
        """
        Ensures that power queries has been successfully
        submitted by power provider.
        """
        self.mocked_cluster_node_information.get_cluster_state_info.\
            return_value = (
                "partially_up", {"key1": [], "key2": []})
        for command in SsplHlProviderPower.POWER_COMMAND:
            ipmitool_command_param = PowerProvider.IPMI_CMD
            selection_args = {'command': command,
                              'debug': True}
            ipmitool_command = self.INTERNAL_COMMAND.get(
                selection_args['command'], selection_args['command']
            )
            ipmitool_command_param = '{} {}'.format(
                ipmitool_command_param,
                ipmitool_command
            )
            with mock.patch('sspl_hl.providers.power.provider.ShellCommand',
                            spec=ShellCommand) as shell_patch:
                shell_command_mock = mock.MagicMock()
                shell_patch.return_value = shell_command_mock
                power_provider = PowerProvider(
                    'power', '',
                    self.mocked_cluster_node_information)
                request_obj = SsplHlProviderPower._get_mock_request_object(
                    command
                )
                power_provider.render_query(request=request_obj)
                shell_command_mock.run_command.assert_called_with(
                    ipmitool_command_param
                )

    def test_bad_command(self):
        """
        Ensure sending a bad command results in appropriate error message.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly using rest based request.
        """
        command = 'invalid_command'
        response_msg = "Error: Invalid command: 'invalid_command'"
        self.mocked_cluster_node_information.get_cluster_state_info.\
            return_value = (
                "partially_up", {"key1": [], "key2": []})
        with mock.patch('sspl_hl.providers.power.provider.ShellCommand',
                        spec=ShellCommand):

            request_mock = SsplHlProviderPower._get_mock_request_object(
                command
            )
            power_provider = PowerProvider(
                'power', '',
                self.mocked_cluster_node_information)
            power_provider.render_query(request=request_mock)
            request_mock.responder.reply_exception.assert_called_once_with(
                response_msg
            )

    def test_extra_service_params(self):
        """
        Ensure sending extra query params results in appropriate error
        message.

        The cli should prevent this from happening, so this is just to
        cover the case of the user bypassing the cli and accessing the
        data provider directly.
        """
        self.mocked_cluster_node_information.get_cluster_state_info.\
            return_value = (
                "partially_up", {"key1": [], "key2": []})
        command_args = {'command': 'on',
                        'debug': True,
                        'ext': 'up'}
        response_msg = \
            "Error: Invalid request: Extra parameter 'ext' detected"

        with mock.patch('sspl_hl.providers.power.provider.ShellCommand',
                        spec=ShellCommand):

            request_mock = SsplHlProviderPower._get_mock_request_object('')
            request_mock.selection_args = command_args
            power_provider = PowerProvider(
                'power', '',
                self.mocked_cluster_node_information)
            power_provider.render_query(request=request_mock)
            request_mock.responder.reply_exception.assert_called_once_with(
                response_msg
            )

    def test_missing_command(self):
        """
        Ensure sending query without command results in an http error
        code.

        The cli should prevent this from happening, so this is just
        to cover the case of the user bypassing the cli and accessing
        the data provider directly.
        """
        self.mocked_cluster_node_information.get_cluster_state_info.\
            return_value = (
                "partially_up", {"key1": [], "key2": []})
        command_args = {'debug': True}

        response_msg = \
            "Error: Invalid request: Missing mandatory args: command"

        with mock.patch('sspl_hl.providers.power.provider.ShellCommand',
                        spec=ShellCommand):

            request_mock = SsplHlProviderPower._get_mock_request_object('')
            request_mock.selection_args = command_args
            power_provider = PowerProvider(
                'power', '',
                self.mocked_cluster_node_information)
            power_provider.render_query(request=request_mock)
            request_mock.responder.reply_exception.assert_called_once_with(
                response_msg
            )

if __name__ == '__main__':
    unittest.main()
