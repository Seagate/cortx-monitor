""" Unit tests for sspl_hl.providers.service.provider """


import unittest
import mock
from sspl_hl.providers.power.provider import PowerProvider


from base_unit_test import BaseUnitTest


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

    def test_power_queries(self):
        """
        Ensures that power queries has been successfully
        submitted by power provider.
        """
        for command in SsplHlProviderPower.POWER_COMMAND:
            ipmitool_command_param = \
                "sudo -u plex /usr/local/bin/ipmitooltool.sh ".split()
            selection_args = {'command': command,
                              'debug': True}
            ipmitool_command = self.INTERNAL_COMMAND.get(
                selection_args['command'], selection_args['command']
            )
            ipmitool_command_param.append(ipmitool_command)
            with mock.patch('subprocess.call', return_value=0) as patch:
                power_provider = PowerProvider('power', '')
                # pylint: disable=protected-access
                self._query_provider(args=selection_args,
                                     provider=power_provider)
                patch.assert_called_with(
                    ipmitool_command_param
                )

    def test_bad_command(self):
        """
        Ensure sending a bad command results in appropriate error message.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly using rest based request.
        """
        command_args = {'command': 'invalid_command', 'debug': True}
        response_msg = "Error: Invalid command: 'invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         PowerProvider('Power', ''))

    def test_extra_service_params(self):
        """
        Ensure sending extra query params results in appropriate error
        message.

        The cli should prevent this from happening, so this is just to
        cover the case of the user bypassing the cli and accessing the
        data provider directly.
        """
        command_args = {'command': 'on',
                        'debug': True,
                        'ext': 'up'}
        response_msg = \
            "Error: Invalid request: Extra parameter 'ext' detected"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         PowerProvider('Power', ''))

    def test_missing_command(self):
        """
        Ensure sending query without command results in an http error
        code.

        The cli should prevent this from happening, so this is just
        to cover the case of the user bypassing the cli and accessing
        the data provider directly.
        """
        response_msg = \
            "Error: Invalid request: Missing command"
        command_args = {'target': 'node*',
                        'debug': True}

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         PowerProvider('Power', ''))

if __name__ == '__main__':
    unittest.main()
