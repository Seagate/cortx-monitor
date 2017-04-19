""" Unit tests for sspl_hl.providers.s3_account.provider """

import unittest
from twisted.internet import defer
from sspl_hl.providers.s3_account.provider import S3AccountProvider
from base_unit_test import BaseUnitTest
import mock


class FakeError(BaseException):
    """
    Fake error - any error.
    """

    def __init__(self, *args, **kwargs):
        super(FakeError, self).__init__(*args, **kwargs)


class SsplHlProviderS3Account(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.s3_account.provider.S3AccountProvider object.
    """

    def test_handleRequest(self):
        """ Ensure request from s3admin subcommand is received
        and processed further.
        """
        request_mock = mock.MagicMock()
        s3account_provider = S3AccountProvider("account", "handling account")
        s3account_provider.render_query = mock.MagicMock()
        s3account_provider.handleRequest(request_mock)
        s3account_provider.render_query.assert_called_once_with(request_mock)

    def test_render_query(self):
        """ Ensure request from handleRequest function is received
        and processed further.
        """
        request_mock = mock.MagicMock()
        s3account_provider = S3AccountProvider("account", "handling account")
        s3account_provider.process_s3admin_request = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format("sspl_hl.utils",
                                          "base_castor_provider",
                                          "BaseCastorProvider.render_query"),
                        return_value=True):
            s3account_provider.render_query(request_mock)
            s3account_provider.process_s3admin_request.assert_called_once_with(
                request_mock)


class SsplHlProviderS3Account_create(BaseUnitTest):
    account_create_response = {
        "Status": "Active",
        "RootUserName": "root",
        "CanonicalId": "kRttyc-MReqvtfF-H9Qs0g",
        "AccountName": "UT_Test",
        "RootSecretKeyId": "EChcJFni8rANscumlQnvCYUPtg3Yr2cT3lI_wx_i",
        "AccessKeyId": "8wHujp32QQiHdanXGIWgSg",
        "AccountId": "hzqUcLbrQ2ybs5Q3ycX9xA"
    }

    @mock.patch('sspl_hl.providers.s3_account.provider.get_client')
    def test_process_s3admin_request_success(self, get_client_mock):
        """ Ensure request is parsed and directed towards further respective
        functions according to action parameter.
        """
        request_mock = mock.MagicMock()
        get_client_mock.return_value = mock.MagicMock(), "Fake_response"
        command_args = {'command': 'account', 'action': 'create',
                        'name': 'UT_Test', 'email': 'ut@test.com'}
        request_mock.selection_args = command_args
        s3account_provider = S3AccountProvider("account", "handling account")
        s3account_provider.execute_command = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format(
                        "sspl_hl.utils", "message_utils",
                        "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3account_provider.process_s3admin_request(request_mock)
            self.assertEqual(response_mock.call_count, 0)
            self.assertEqual(request_mock.reply.call_count, 0)
            self.assertEqual(s3account_provider.execute_command.call_count, 1)

    @mock.patch('sspl_hl.providers.s3_account.provider.get_client')
    def test_process_s3admin_request_failure(self, get_client_mock):
        """ Ensure request is parsed and directed towards further respective
        functions according to action parameter.
        """
        request_mock = mock.MagicMock()
        get_client_mock.return_value = None, "Fake_response"
        command_args = {'command': 'account', 'action': 'create',
                        'name': 'UT_Test', 'email': 'ut@test.com'}
        request_mock.selection_args = command_args
        s3account_provider = S3AccountProvider("account", "handling account")
        s3account_provider.execute_command = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format(
                        "sspl_hl.utils", "message_utils",
                        "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3account_provider.process_s3admin_request(request_mock)
            self.assertEqual(response_mock.call_count, 1)
            self.assertEqual(request_mock.reply.call_count, 1)
            self.assertEqual(s3account_provider.execute_command.call_count, 0)

    def test_create_account_command_success(self):
        """ Ensure request is received and parameters are processes to form
        a query. Ensure that according to received response,(in this case
         success)further function is called to generate desired output.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'account', 'action': 'create',
                        'name': 'UT_Test', 'email': 'ut@test.com'}
        request_mock.selection_args = command_args
        s3account_provider = S3AccountProvider("account", "handling account")
        s3account_provider._handle_success = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_account.provider.deferToThread",
                        return_value=defer.succeed(
                            self.account_create_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "account_handler",
                                              "AccountUtility.create")) \
                    as account_create_handler_mock:
                s3account_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'create')
                self.assertEqual(account_create_handler_mock.call_count, 1)

    def test_create_account_command_failure(self):
        """Ensure request is received and parameters are processes to form
        a query. Ensure that according to received response,(in this case
         failure)further function is called to generate reason of failure
         and its description.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'account', 'action': 'create',
                        'name': 'UT_Test', 'email': 'ut@test.com'}
        request_mock.selection_args = command_args
        s3account_provider = S3AccountProvider("account", "handling account")
        s3account_provider._handle_failure = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_account.provider.deferToThread",
                        return_value=defer.fail(FakeError('error'))):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "account_handler",
                                              "AccountUtility.create")) \
                    as account_create_handler_mock:
                s3account_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'create')
                self.assertEqual(account_create_handler_mock.call_count, 1)
                self.assertEqual(s3account_provider._handle_failure.call_count,
                                 1)

    def test_handle_create_success(self):
        """ When account create is successful, ensure that further function is
        called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3account_provider = S3AccountProvider("account", "handling account")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3account_provider._handle_success(
                self.account_create_response, request_mock)
            response_mock.assert_called_once_with(self.account_create_response)
            self.assertEqual(request_mock.reply.call_count, 1)


class SsplHlProviderS3Account_list(BaseUnitTest):
    account_list_response = [
        {
            "AccountId": "zU0B1Uy4RiaMOXMgWVKIDg",
            "Email": "vikram.chhajer@seagate.com",
            "CanonicalId": "KuvWsH7URB2wEN36JIPIxA",
            "AccountName": "Vikram"
        },
        {
            "AccountId": "qN3a1bhPSByEDrGsm2hMUA",
            "Email": "priti.deshmukh@seagate.com",
            "CanonicalId": "RSqUCOQ1SfGHLkPBo0b7wQ",
            "AccountName": "Priti"
        }
    ]

    def test_execute_list_command_success(self):
        """Ensure request is received and parameters are processes to form
        a query. Ensure that according to received response,(in this case
        success)further function is called to generate desired output.
        """

        request_mock = mock.MagicMock()
        command_args = {'command': 'account', 'action': 'list'}
        request_mock.selection_args = command_args
        s3account_provider = S3AccountProvider("account", "handling account")
        s3account_provider._handle_success = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_account.provider.deferToThread",
                        return_value=defer.succeed(
                            self.account_list_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "account_handler",
                                              "AccountUtility.list")) \
                    as account_list_handler_mock:
                s3account_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'list')
                self.assertEqual(account_list_handler_mock.call_count, 1)
                s3account_provider._handle_success.assert_called_with(
                    self.account_list_response, request_mock)

    def test_execute_list_command_failure(self):
        """Ensure request is received and parameters are processes to form
        a query. Ensure that according to received response,(in this case
         failure)further function is called to generate reason of failure
         and its description.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'account', 'action': 'list'}
        request_mock.selection_args = command_args
        s3account_provider = S3AccountProvider("account", "handling account")
        s3account_provider._handle_list_failure = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_account.provider.deferToThread",
                        return_value=defer.fail(FakeError('error'))):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "account_handler",
                                              "AccountUtility.list")) \
                    as account_list_handler_mock:
                s3account_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'list')
                self.assertEqual(account_list_handler_mock.call_count, 1)

    def test_handle_list_succes(self):
        """When account list request is processed successfully,
        ensure that further function is called to process the
        recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3account_provider = S3AccountProvider("account", "handling account")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3account_provider._handle_success(
                self.account_list_response, request_mock)
            response_mock.assert_called_once_with(self.account_list_response)
            self.assertEqual(request_mock.reply.call_count, 1)


if __name__ == '__main__':
    unittest.main()
