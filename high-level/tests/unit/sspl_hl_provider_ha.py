""" Unit tests for sspl_hl.providers.service.provider """


import unittest
import mock
import subprocess
import os
import signal

from sspl_hl.providers.ha.provider import HaProvider
from base_unit_test import BaseUnitTest


# pylint: disable=too-many-public-methods
class SsplHlProviderHa(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.service.provider.HaProvider object.
    """
    HA_COMMAND = ['debug']

    # pylint: disable=no-self-use
    def _create_provider(self):
        ha_provider = HaProvider('ha', '')
        ha_provider.on_create()
        return ha_provider

    @staticmethod
    def _start_fake_frontier():
        """
        Start the fake frontier service
        """
        proc = subprocess.Popen(
            ['./tests/fake_halond/frontier.py',
             '-p',
             '/tmp/frontier.pid'],
            preexec_fn=os.setsid
        )
        return proc

    @staticmethod
    def _stop_fake_frontier(proc):
        """
        Stop the fake frontier service
        @param proc: process
        @type proc: subprocess.process
        """
        os.killpg(proc.pid, signal.SIGTERM)

    @mock.patch('twisted.internet.reactor.callFromThread')
    def test_rg_reply(self, call_patch):
        """
        Test resource graph fetch from frontier service.
        Ensure reply is called
        """
        # pylint: disable=protected-access
        proc = SsplHlProviderHa._start_fake_frontier()
        ha_provider = self._create_provider()
        responder = mock.MagicMock()
        self._query_provider(
            {'command': 'debug', 'subcommand': 'show'},
            responder,
            ha_provider
        )
        SsplHlProviderHa._stop_fake_frontier(proc)
        args, kwargs = call_patch.call_args
        self.assertFalse(kwargs == {})
        self.assertTrue(responder.reply in args)

    @mock.patch('twisted.internet.reactor.callFromThread')
    def test_rg_exception(self, call_patch):
        """
        Test resource graph fetch from frontier service.
        Ensure reply_exception is called since
        fake frontier service is not running.
        """
        # pylint: disable=protected-access
        ha_provider = self._create_provider()
        responder = mock.MagicMock()
        ha_provider._get_resource_graph(responder)
        args, kwargs = call_patch.call_args
        self.assertTrue(kwargs == {})
        self.assertTrue(responder.reply_exception in args)

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'invalid_command', 'subcommand': 'show'}
        response_msg = "Error: Invalid command: 'invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         HaProvider('ha', ''))

    def test_extra_service_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'debug',
                        'subcommand': 'show',
                        'ext': 'up'}
        response_msg = "Error: Invalid request: Extra parameter 'ext' detected"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         HaProvider('ha', ''))

    def test_missing_subcommand(self):
        """ Ensure sending query without service name results in an http error
        code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'command': 'debug'}
        response_msg = "Error: Invalid request: Missing subcommand"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         HaProvider('ha', ''))

    def test_missing_command(self):
        """ Ensure sending query without command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        command_args = {'subcommand': 'show'}
        response_msg = "Error: Invalid request: Missing command"
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         HaProvider('ha', ''))


if __name__ == '__main__':
    unittest.main()
