""" Unit tests for sspl_hl.providers.support_bundle.provider """


import unittest
from twisted.internet import defer
from sspl_hl.providers.bundle.provider import SupportBundleProvider
from base_unit_test import BaseUnitTest
import mock


class FakeError(BaseException):
    """
    Fake error - any error.
    """

    def __init__(self, *args, **kwargs):
        super(FakeError, self).__init__(*args, **kwargs)


# pylint: disable=too-many-public-methods
class SsplHlProviderSupportBundle(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.support_bundle.provider.SupportBundleProvider object.
    """
    COMMAND = ['create', 'list']

    def test_bundle_list_success(self):
        """ Ensure 'bundle list' command gives expected response
            and verify the request.reply count.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'list'}
        request_mock.selection_args = command_args
        bundle_provider = SupportBundleProvider('bundle', 'test_bundle')
        with mock.patch(
            "sspl_hl.utils.support_bundle.bundle_utils.get_bundle_info"), \
            mock.patch("sspl_hl.providers.bundle.provider.deferToThread",
                       return_value=defer.succeed(["Bundle1, Bundle2"])):
            bundle_provider.render_query(request_mock)
            self.assertEqual(request_mock.reply.call_count, 1)

    def test_bundle_list_failure(self):
        """ Ensure 'bundle list' command gives expected response
            for failure and verify the request.responder.reply_exception count.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'list'}
        request_mock.selection_args = command_args
        bundle_provider = SupportBundleProvider('bundle', 'test_bundle')
        with mock.patch(
            "sspl_hl.utils.support_bundle.bundle_utils.get_bundle_info"), \
            mock.patch("sspl_hl.providers.bundle.provider.deferToThread",
                       return_value=defer.fail(FakeError('error'))):
            bundle_provider.render_query(request_mock)
            self.assertEqual(
                request_mock.responder.reply_exception.call_count, 1)

    def test_bundle_create_success(self):
        """ Ensure 'bundle create' command gives expected response
            and verify the request.reply count.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'create'}
        request_mock.selection_args = command_args
        bundle_provider = SupportBundleProvider('bundle', 'test_bundle')
        with mock.patch('{}.{}.{}'.format(
            "sspl_hl.utils.support_bundle",
            "support_bundle_handler",
            "SupportBundleHandler.collect")) \
                as handler_mock:
            bundle_provider.render_query(request_mock)
            self.assertEqual(handler_mock.call_count, 1)

    def test_bundle_create_failure(self):
        """ Ensure 'bundle create' command gives expected response
            and verify the request.reply count.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'create'}
        request_mock.selection_args = command_args
        bundle_provider = SupportBundleProvider('bundle', 'test_bundle')
        with mock.patch('{}.{}.{}'.format(
            "sspl_hl.utils.support_bundle",
            "support_bundle_handler",
            "SupportBundleHandler.collect")) \
                as bundle_handler:
            bundle_provider.render_query(request_mock)
            self.assertEqual(
                bundle_handler.call_count,
                1
            )

    def test_bad_command(self):
        """ Ensure sending a bad command results in an http error code.
        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """

        command_args = {'command': 'invalid_command'}
        response_msg = "Error: Invalid command: 'invalid_command'"

        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         SupportBundleProvider(
                                             'support_bundle', ''))

    def test_extra_params(self):
        """ Ensure sending extra query params results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data provider
        directly.
        """

        command_args = {'command': 'list',
                        'extra': 'extra'}
        main_msg = "Error: Invalid request:"
        response_msg = " Extra parameter 'extra' detected"

        self._test_args_validation_cases(command_args,
                                         main_msg + response_msg,
                                         SupportBundleProvider(
                                             'support_bundle', ''))

    def test_missing_command(self):
        """
        Ensure sending query without command results in an http error code.

        The cli should prevent this from happening, so this is just to cover
        the case of the user bypassing the cli and accessing the data
        provider directly.
        """

        command_args = {''}
        response_msg = "Error: Invalid request: Unsupported args "
        self._test_args_validation_cases(command_args,
                                         response_msg,
                                         SupportBundleProvider(
                                             'support_bundle', ''))


if __name__ == '__main__':
    unittest.main()
