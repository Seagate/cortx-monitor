"""Unit tests for sspl_hl.providers.ha.provider.HaProvider"""

import unittest
import mock
import socket
import subprocess
import time
from sspl_hl.providers.ha.provider import HaProvider
from base_unit_test import BaseUnitTest
# pylint: disable=too-many-public-methods


class SsplHlProviderHa(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.ha.provider.HaProvider object.
    """

    @classmethod
    def setUpClass(cls):
        cls.fsproc = None
        if not cls._verify_frontier_running():
            cls.fsproc = cls._start_fake_frontier()

    @classmethod
    def tearDownClass(cls):
        if cls.fsproc is not None:
            cls._stop_frontier(cls.fsproc)

    @staticmethod
    def _query_provider(args,
                        responder=mock.MagicMock(),
                        provider=None):
        super(SsplHlProviderHa, SsplHlProviderHa)._query_provider(
            args,
            responder,
            HaProvider('Ha', ''))

    @classmethod
    def _unpack_response_data(cls, res_data):
        if res_data is not None:
            if res_data['Response Data'] is not None:
                # pylint: disable=unused-variable
                rd_args = res_data['Response Data'][1]
                if 'data' in rd_args:
                    data = rd_args['data'][0]
                    if 'label' in data:
                        return 1
        return 0

    @staticmethod
    def _verify_frontier_running():
        try:
            conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            conn.connect(('127.0.0.1', 9008))
            conn.close()
            return True
        except socket.error:
            return False

    @staticmethod
    def _start_fake_frontier():
        proc = subprocess.Popen(
            ['./tests/fake_halond/frontier.py',
             '-p',
             '/tmp/frontier.pid']
        )

        # wait for frontier service to become available
        timeout = 5
        poll_interval = 0.1
        while not SsplHlProviderHa._verify_frontier_running():
            time.sleep(poll_interval)
            timeout -= poll_interval
            if timeout < 0:
                raise RuntimeError("Unable to start fake frontier service")

        return proc

    @staticmethod
    def _stop_frontier(proc):
        proc.terminate()

    def _test_ha_query(self, command, subcommand):

        self._query_provider(
            args={'command': command, 'subcommand': subcommand, 'action': 'ha'}
            )

    @mock.patch('pika.BlockingConnection')
    @mock.patch('twisted.internet.reactor.callFromThread')
    def test_ha_debug_show(self, cft_patch, conn_patch):
        """ Ensures cstor ha debug show command execution.
        """
        result = {}
        nodes_avlb = None
        self._test_ha_query('debug', 'show')
        result['Called Status'] = cft_patch.called
        result['Response Data'] = cft_patch.call_args
        nodes_avlb = self._unpack_response_data(result)
        if result is not None:
            self.assertTrue(result['Called Status'])
        self.assertEqual(nodes_avlb, 1)
        self.assertFalse(conn_patch().channel().basic_publish.called)

    @mock.patch('pika.BlockingConnection')
    @mock.patch('twisted.internet.reactor.callFromThread')
    def test_ha_debug_status(self, cft_patch, conn_patch):
        """ Ensures cstor ha debug status command execution.
        """
        result = {}
        nodes_avlb = None
        self._test_ha_query('debug', 'status')
        result['Called Status'] = cft_patch.called
        result['Response Data'] = cft_patch.call_args
        nodes_avlb = self._unpack_response_data(result)
        if result is not None:
            self.assertTrue(result['Called Status'])
        self.assertEqual(nodes_avlb, 1)
        self.assertFalse(conn_patch().channel().basic_publish.called)

    @mock.patch('pika.BlockingConnection')
    @mock.patch('twisted.internet.reactor.callFromThread')
    def test_ha_info_show(self, cft_patch, conn_patch):
        """ Ensures cstor ha info show command execution.
        """
        result = {}
        nodes_avlb = None
        self._test_ha_query('info', 'show')
        result['Called Status'] = cft_patch.called
        result['Response Data'] = cft_patch.call_args
        nodes_avlb = self._unpack_response_data(result)
        if result is not None:
            self.assertTrue(result['Called Status'])
        self.assertEqual(nodes_avlb, 1)
        self.assertFalse(conn_patch().channel().basic_publish.called)

    @mock.patch('pika.BlockingConnection')
    @mock.patch('twisted.internet.reactor.callFromThread')
    def test_ha_info_status(self, cft_patch, conn_patch):
        """ Ensures cstor ha info status command execution.
        """
        result = {}
        nodes_avlb = None
        self._test_ha_query('info', 'status')
        result['Called Status'] = cft_patch.called
        result['Response Data'] = cft_patch.call_args
        nodes_avlb = self._unpack_response_data(result)
        if result is not None:
            self.assertTrue(result['Called Status'])
        self.assertEqual(nodes_avlb, 1)
        self.assertFalse(conn_patch().channel().basic_publish.called)

    @mock.patch('pika.BlockingConnection')
    @mock.patch('twisted.internet.reactor.callFromThread')
    def test_bad_command(self, cft_patch, conn_patch):
        """ Ensure sending a bad command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        result = {}
        nodes_avlb = None
        self._query_provider(
            args={
                'command': 'invalid_command'
                },
            )
        result['Response Data'] = cft_patch.call_args
        nodes_avlb = self._unpack_response_data(result)
        self.assertEqual(nodes_avlb, 0)
        self.assertFalse(conn_patch().channel().basic_publish.called)

    @mock.patch('pika.BlockingConnection')
    @mock.patch('twisted.internet.reactor.callFromThread')
    def test_extra_params(self, cft_patch, conn_patch):
        """ Ensure extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        thng the cli and accessing the data provider
        directly.
        """
        result = {}
        nodes_avlb = None
        self._query_provider(
            args={
                'command': 'debug',
                'subcommand': 'info',
                'action': 'ha',
                'extraargs': 'blah'
                },
        )
        result['Response Data'] = cft_patch.call_args
        nodes_avlb = self._unpack_response_data(result)
        self.assertEqual(nodes_avlb, 0)
        self.assertFalse(conn_patch().channel().basic_publish.called)

if __name__ == '__main__':
    unittest.main(verbosity=2)
