""" Unit tests for sspl_hl.providers.status.provider """
import unittest
import mock
from twisted.internet import defer
from base_unit_test import BaseUnitTest
from sspl_hl.providers.status.provider import StatusProvider


# pylint: disable=too-many-public-methods
class SsplHlProviderStatus(BaseUnitTest):
    """
    Test methods of the
    sspl_hl.providers.status.provider.StatusProvider object.
    """

    # pylint: disable=protected-access
    def _test_defer(self, command_args, reply_call_count, defer_call_count):
        """ Tests for defer calls in status provider
        """
        request_mock = mock.MagicMock()
        request_mock.selection_args = command_args
        provider = StatusProvider('status', '')
        msg = provider._generate_fs_status_req_msg()
        with mock.patch(
                "sspl_hl.providers.status.provider.deferToThread",
                return_value=defer.succeed(msg)) as defer_mock:
            provider.create_data_receiver = mock.MagicMock()
            # pylint: disable=invalid-name
            d = defer.Deferred()
            provider.receiver = mock.MagicMock()
            provider.receiver.query = mock.MagicMock(name='query')
            provider.receiver.query.return_value = d
            provider.render_query(request=request_mock)
            self.assertEqual(request_mock.reply.call_count, reply_call_count)
            self.assertEqual(defer_mock.call_count, defer_call_count)

    def test_queries(self):
        """ Test defer calls to power, RAS SEM and file system status
        """
        self._test_defer({'command': 'ipmi', 'debug': 'false'}, 1, 3)

    def test_invalid_command(self):
        """ Test for invalid command argument
        """
        self._test_defer({'command': 'invalid', 'debug': 'false'}, 0, 0)

    def test_missing_command(self):
        """ Test for missing command value
        """
        self._test_defer({'debug': 'false'}, 0, 0)

    def test_extra_args(self):
        """ Test for extra args passed to render_query
        """
        self._test_defer(
            {'command': 'ipmi', 'debug': 'false', 'extra': 'val'}, 0, 0)

if __name__ == '__main__':
    unittest.main()
