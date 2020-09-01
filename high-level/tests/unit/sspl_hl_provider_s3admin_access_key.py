# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

""" Unit tests for sspl_hl.providers.s3_access_key.provider """

import unittest
from twisted.internet import defer
from sspl_hl.providers.s3_access_key.provider import S3AccessKeyProvider
from base_unit_test import BaseUnitTest
import mock


class FakeError(BaseException):
    """
    Fake error - any error.
    """

    def __init__(self, *args, **kwargs):
        super(FakeError, self).__init__(*args, **kwargs)


class SsplHlProviderS3AccessKey(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.s3_access_key.provider.S3AccessKeyProvider object.
    """

    def test_handleRequest(self):
        """ Ensure request from s3admin subcommand is received
        and processed further.
        """
        request_mock = mock.MagicMock()
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        s3access_key_provider.render_query = mock.MagicMock()
        s3access_key_provider.handleRequest(request_mock)
        s3access_key_provider.render_query.assert_called_once_with(
            request_mock)

    def test_render_query(self):
        """ Ensure request from handleRequest function is received
        and processed further.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'access_key',
            'action': 'create',
            'user_name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        access_key_provider = S3AccessKeyProvider("access_key",
                                                  "handling access_key")
        action = request_mock.selection_args.get('action', None)
        self.assertEqual(action, 'create')
        access_key_provider.process_s3auth_request = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format("sspl_hl.utils",
                                          "base_castor_provider",
                                          "BaseCastorProvider.render_query"),
                        return_value=True):
            access_key_provider.render_query(request_mock)
            access_key_provider.process_s3auth_request.assert_called_once_with(
                request_mock)


class SsplHlProviderS3AccessKey_create(BaseUnitTest):
    access_key_create_response = {
        "UserName": "admin",
        "Status": "Active",
        "AccessKey": "8wHujp32QQiHdanXGIWgSg",
        "SecretKey": "EChcJFni8rANscumlQnvCYUPtg3Yr2cT3lI_wx_i"
    }

    @mock.patch('sspl_hl.providers.s3_access_key.provider.get_client')
    def test_process_s3admin_request_success(self, get_client_mock):
        """ Ensure process the request bundle request based on the command
        """
        get_client_mock.return_value = mock.MagicMock(), "Fake_response"
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'access_key',
            'action': 'create',
            'user_name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        s3access_key_provider.execute_command = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3access_key_provider.process_s3auth_request(request_mock)
            self.assertEqual(response_mock.call_count, 0)
            self.assertEqual(request_mock.reply.call_count, 0)
            self.assertEqual(s3access_key_provider.execute_command.call_count,
                             1)

    @mock.patch('sspl_hl.providers.s3_access_key.provider.get_client')
    def test_process_s3admin_request_failure(self, get_client_mock):
        """ Ensure process the request bundle request based on the command
        """
        get_client_mock.return_value = None, "Fake_response"
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'access_key',
            'action': 'create',
            'user_name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        s3access_key_provider.execute_command = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3access_key_provider.process_s3auth_request(request_mock)
            self.assertEqual(response_mock.call_count, 1)
            self.assertEqual(request_mock.reply.call_count, 1)
            self.assertEqual(s3access_key_provider.execute_command.call_count,
                             0)

    def test_execute_command_success(self):
        """Ensure execution of thread based on s3access_key
        operation request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'access_key',
            'action': 'create',
            'user_name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        s3access_key_provider._handle_success = mock.MagicMock()
        with mock.patch(
                "sspl_hl.providers.s3_access_key.provider.deferToThread",
                return_value=defer.succeed(
                    self.access_key_create_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "access_key_handler",
                                              "AccessKeyUtility.create")) \
                    as access_key_create_handler_mock:
                s3access_key_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'create')
                s3access_key_provider._handle_success.assert_called_once_with(
                    self.access_key_create_response, request_mock)

    def test_execute_command_failure(self):
        """Handle failure while execution of thread based on s3access_key
        operation request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'access_key',
            'action': 'create',
            'user_name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        s3access_key_provider._handle_failure = mock.MagicMock()
        with mock.patch(
                "sspl_hl.providers.s3_access_key.provider.deferToThread",
                return_value=defer.fail(FakeError('error'))):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "access_key_handler",
                                              "AccessKeyUtility.create")) \
                    as access_key_create_handler_mock:
                s3access_key_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'create')
                self.assertEqual(
                    s3access_key_provider._handle_failure.call_count, 1)

    def test_handle_success(self):
        """ When access_key create is successful, ensure that further
        function is called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3access_key_provider._handle_success(
                self.access_key_create_response,
                request_mock)
            response_mock.assert_called_once_with(
                self.access_key_create_response)
            self.assertEqual(request_mock.reply.call_count, 1)


class SsplHlProviderS3AccessKey_list(BaseUnitTest):
    access_key_list_response = [{
        "UserName": "admin",
        "Status": "Active",
        "AccessKey": "8wHujp32QQiHdanXGIWgSg"
    },
        {
            "UserName": "admin",
            "Status": "Active",
            "AccessKey": "8wHujp32QQiHdanXGIWgSg"
        }]

    def test_execute_command_success(self):
        """Ensure execution of thread based on s3access_key operation
        request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'access_key',
            'action': 'list',
            'user_name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        s3access_key_provider._handle_success = mock.MagicMock()
        with mock.patch(
                "sspl_hl.providers.s3_access_key.provider.deferToThread",
                return_value=defer.succeed(
                    self.access_key_list_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "access_key_handler",
                                              "AccessKeyUtility.list")) \
                    as access_key_list_handler_mock:
                s3access_key_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'list')
                s3access_key_provider._handle_success.assert_called_once_with(
                    self.access_key_list_response, request_mock)

    def test_handle_list_success(self):
        """ When access_key list is successful, ensure that further function is
        called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3access_key_provider._handle_success(
                self.access_key_list_response,
                request_mock)
            response_mock.assert_called_once_with(
                self.access_key_list_response)
            self.assertEqual(request_mock.reply.call_count, 1)


class SsplHlProviderS3AccessKey_modify(BaseUnitTest):
    def test_execute_command_success(self):
        """Ensure execution of thread based on s3access_key operation
        request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'access_key',
            'action': 'modify',
            'user_name': 'test',
            'status': 'Active',
            'user_access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'access_key': 'eGdkxW3QScC5ZU4EUnTRkg',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'

        }
        request_mock.selection_args = command_args
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        s3access_key_provider._handle_success = mock.MagicMock()
        with mock.patch(
                "sspl_hl.providers.s3_access_key.provider.deferToThread",
                return_value=defer.succeed(
                    SsplHlProviderS3AccessKey_list.access_key_list_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "access_key_handler",
                                              "AccessKeyUtility.modify")) \
                    as access_key_modify_handler_mock:
                s3access_key_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'modify')
                s3access_key_provider._handle_success.assert_called_once_with(
                    SsplHlProviderS3AccessKey_list.access_key_list_response,
                    request_mock)

    def test_handle_modify_success(self):
        """ When access_key modify is successful, ensure that further
        function is called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3access_key_provider._handle_success(
                SsplHlProviderS3AccessKey_list.access_key_list_response,
                request_mock)
            response_mock.assert_called_once_with(
                SsplHlProviderS3AccessKey_list.access_key_list_response)
            self.assertEqual(request_mock.reply.call_count, 1)


class SsplHlProviderS3AccessKey_remove(BaseUnitTest):
    def test_execute_command_success(self):
        """Ensure execution of thread based on s3access_key operation
        request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'access_key',
            'action': 'remove',
            'user_name': 'test',
            'user_access_key': 'eGdkxW3QScC5ZU4EUnTRkg',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        s3access_key_provider._handle_success = mock.MagicMock()
        with mock.patch(
                "sspl_hl.providers.s3_access_key.provider.deferToThread",
                return_value=defer.succeed(
                    SsplHlProviderS3AccessKey_list.access_key_list_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "access_key_handler",
                                              "AccessKeyUtility.remove")) \
                    as access_key_remove_handler_mock:
                s3access_key_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'remove')
                s3access_key_provider._handle_success.assert_called_once_with(
                    SsplHlProviderS3AccessKey_list.access_key_list_response,
                    request_mock)

    def test_handle_modify_success(self):
        """ When access_key remove is successful, ensure that further
        function is called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3access_key_provider = S3AccessKeyProvider("access_key",
                                                    "handling access_key")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3access_key_provider._handle_success(
                SsplHlProviderS3AccessKey_list.access_key_list_response,
                request_mock)
            response_mock.assert_called_once_with(
                SsplHlProviderS3AccessKey_list.access_key_list_response
            )
            self.assertEqual(request_mock.reply.call_count, 1)


if __name__ == '__main__':
    unittest.main()
