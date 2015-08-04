"""Unit tests for sspl_hl.providers.ha.provider"""

import unittest
import mock
from sspl_hl.providers.ha.provider import HaProvider
from base_unit_test import BaseUnitTest
# pylint: disable=too-many-public-methods


class SsplHlProviderHa(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.ha.provider.HaProvider object.
    """

    @staticmethod
    def _query_provider(args, responder=mock.MagicMock(),
                        provider=None):
        super(SsplHlProviderHa, SsplHlProviderHa)._query_provider(
            args,
            responder,
            HaProvider('Ha', ''))
        response_data = {
            'Called Status': responder.reply.called,
            'Response Data': responder.reply.call_args
        }
        return response_data

    @classmethod
    def _unpack_response_data(cls, res_data):
        if res_data['Response Data'] is not None:
            # pylint: disable=unused-variable
            (rd_args, rd_kwargs) = res_data['Response Data']
            data = rd_kwargs['data'][0]
            if 'message' in data:
                if 'statusResponse' in data['message']:
                    msg = data['message']
                    if 'items' in msg['statusResponse']:
                        msg_res = msg['statusResponse']
                        if msg_res['items']:
                            return len(msg_res['items'])
        return 0

    def _test_ha_query(self, command, subcommand):

        res = self._query_provider(
            args={'command': command, 'subcommand': subcommand, 'action': 'ha'}
            )
        return res

    def test_ha_debug_show(self):
        """ Ensures cstor ha debug show command execution.
        """
        test_result_data = self._test_ha_query('debug', 'show')
        test_result_data['Test Name'] = "Test for 'cstor ha debug show' cmnd"
        self.assertTrue(test_result_data['Called Status'])
        nodes = SsplHlProviderHa._unpack_response_data(test_result_data)
        self.assertEqual(nodes, 2)

    def test_ha_debug_status(self):
        """ Ensures cstor ha debug show command execution.
        """
        test_result_data = self._test_ha_query('debug', 'status')
        test_result_data['Test Name'] = "Test for 'cstor ha debug status' cmnd"
        self.assertTrue(test_result_data['Called Status'])
        nodes = SsplHlProviderHa._unpack_response_data(test_result_data)
        self.assertEqual(nodes, 2)

    def test_ha_info_show(self):
        """ Ensures cstor ha info show command execution.
        """
        test_result_data = self._test_ha_query('info', 'show')
        test_result_data['Test Name'] = "Test for 'cstor ha info show' cmnd"
        self.assertTrue(test_result_data['Called Status'])
        nodes = SsplHlProviderHa._unpack_response_data(test_result_data)
        self.assertEqual(nodes, 2)

    def test_ha_info_status(self):
        """ Ensures cstor ha debug show command execution.
        """
        test_result_data = self._test_ha_query('info', 'status')
        test_result_data['Test Name'] = "Test for 'cstor ha info status' cmnd"
        self.assertTrue(test_result_data['Called Status'])
        nodes = SsplHlProviderHa._unpack_response_data(test_result_data)
        self.assertEqual(nodes, 2)

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        test_result_data = self._query_provider(
            args={'command': 'invalid_command'},
            )
        self.assertFalse(test_result_data['Called Status'])
        nodes = SsplHlProviderHa._unpack_response_data(test_result_data)
        self.assertEqual(nodes, 0)

    def test_extra_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """
        test_result_data = self._query_provider(
            args={
                'command': 'debug',
                'subcommand': 'info',
                'action': 'ha',
                'extraargs': 'blah'
                },
            )
        self.assertFalse(test_result_data['Called Status'])
        nodes = SsplHlProviderHa._unpack_response_data(test_result_data)
        self.assertEqual(nodes, 0)

if __name__ == '__main__':
    unittest.main()
