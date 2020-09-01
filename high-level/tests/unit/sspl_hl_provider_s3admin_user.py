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

""" Unit tests for sspl_hl.providers.s3_users.provider """

import unittest
from twisted.internet import defer
from sspl_hl.providers.s3_users.provider import S3UsersProvider
from base_unit_test import BaseUnitTest
import mock


class FakeError(BaseException):
    """
    Fake error - any error.
    """

    def __init__(self, *args, **kwargs):
        super(FakeError, self).__init__(*args, **kwargs)


class SsplHlProviderS3Users(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.s3_users.provider.S3UsersProvider object.
    """

    def test_handleRequest(self):
        """ Ensure request from s3admin subcommand is received
        and processed further.
        """
        request_mock = mock.MagicMock()
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider.render_query = mock.MagicMock()
        s3user_provider.handleRequest(request_mock)
        s3user_provider.render_query.assert_called_once_with(request_mock)

    def test_render_query(self):
        """ Ensure request from handleRequest function is received
        and processed further.
        """
        request_mock = mock.MagicMock()
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider.process_s3admin_request = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format("sspl_hl.utils",
                                          "base_castor_provider",
                                          "BaseCastorProvider.render_query"),
                        return_value=True):
            s3user_provider.render_query(request_mock)
            s3user_provider.process_s3admin_request.assert_called_once_with(
                request_mock)


class SsplHlProviderS3Users_create(BaseUnitTest):
    user_create_response = {
        "UserName": "admin",
        "Path": "/",
        "UserId": "pcM4vMmNRQeYmgaxIm2coQ",
        "Arn": "arn:aws:iam::1:user/admin"
    }

    @mock.patch('sspl_hl.providers.s3_users.provider.get_client')
    def test_process_s3admin_request_success(self, get_client_mock):
        """ Ensure process the request bundle request based on the command
        """
        get_client_mock.return_value = mock.MagicMock(), "Fake_Response"
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'user',
            'action': 'create',
            'name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider.execute_command = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format(
                        "sspl_hl.utils", "message_utils",
                        "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3user_provider.process_s3admin_request(request_mock)
            self.assertEqual(response_mock.call_count, 0)
            self.assertEqual(request_mock.reply.call_count, 0)
            self.assertEqual(s3user_provider.execute_command.call_count, 1)

    @mock.patch('sspl_hl.providers.s3_users.provider.get_client')
    def test_process_s3admin_request_failure(self, get_client_mock):
        """ Ensure process the request bundle request based on the command
        """
        get_client_mock.return_value = None, "Fake_Response"
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'user',
            'action': 'create',
            'name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider.execute_command = mock.MagicMock()
        with mock.patch('{}.{}.{}'.format(
                        "sspl_hl.utils", "message_utils",
                        "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3user_provider.process_s3admin_request(request_mock)
            self.assertEqual(response_mock.call_count, 1)
            self.assertEqual(request_mock.reply.call_count, 1)
            self.assertEqual(s3user_provider.execute_command.call_count, 0)

    def test_execute_command_success(self):
        """Ensure execution of thread based on s3user
        operation request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'user',
            'action': 'create',
            'name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider._handle_success = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_users.provider.deferToThread",
                        return_value=defer.succeed(
                            self.user_create_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "user_handler",
                                              "UsersUtility.create")) \
                    as user_create_handler_mock:
                s3user_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'create')
                s3user_provider._handle_success.assert_called_once_with(
                    self.user_create_response, request_mock)

    def test_execute_command_failure(self):
        """Handle failure while execution of thread based on s3user
        operation request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'user',
            'action': 'create',
            'name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider._handle_failure = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_users.provider.deferToThread",
                        return_value=defer.fail(FakeError('error'))):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "user_handler",
                                              "UsersUtility.create")) \
                    as user_create_handler_mock:
                s3user_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'create')
                self.assertEqual(s3user_provider._handle_failure.call_count, 1)

    def test_handle_success(self):
        """ When user create is successful, ensure that further function is
        called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3user_provider = S3UsersProvider("users", "handling users")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3user_provider._handle_success(self.user_create_response,
                                            request_mock)
            response_mock.assert_called_once_with(self.user_create_response)
            self.assertEqual(request_mock.reply.call_count, 1)


class SsplHlProviderS3Users_list(BaseUnitTest):
    user_list_response = [{
        "UserName": "admin",
        "Path": "/",
        "UserId": "pcM4vMmNRQeYmgaxIm2coQ",
        "Arn": "arn:aws:iam::1:user/admin"
    },
        {
            "UserName": "admin",
            "Path": "/",
            "UserId": "pcM4vMmNRQeYmgaxIm2coQ",
            "Arn": "arn:aws:iam::1:user/admin"
        }]

    def test_execute_command_success(self):
        """Ensure execution of thread based on s3user operation
        request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'user',
            'action': 'list',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider._handle_success = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_users.provider.deferToThread",
                        return_value=defer.succeed(
                            self.user_list_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "user_handler",
                                              "UsersUtility.list")) \
                    as user_list_handler_mock:
                s3user_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'list')
                s3user_provider._handle_success.assert_called_once_with(
                    self.user_list_response, request_mock)

    def test_handle_list_success(self):
        """ When user list is successful, ensure that further function is
        called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3user_provider = S3UsersProvider("users", "handling users")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3user_provider._handle_success(self.user_list_response,
                                            request_mock)
            response_mock.assert_called_once_with(self.user_list_response)
            self.assertEqual(request_mock.reply.call_count, 1)


class SsplHlProviderS3Users_modify(BaseUnitTest):
    def test_execute_command_success(self):
        """Ensure execution of thread based on s3user operation
        request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'user',
            'action': 'modify',
            'name': 'test',
            'new_name': 'test_new',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider._handle_success = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_users.provider.deferToThread",
                        return_value=defer.succeed(
                            SsplHlProviderS3Users_list.user_list_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "user_handler",
                                              "UsersUtility.modify")) \
                    as user_modify_handler_mock:
                s3user_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'modify')
                s3user_provider._handle_success.assert_called_once_with(
                    SsplHlProviderS3Users_list.user_list_response,
                    request_mock)

    def test_handle_modify_success(self):
        """ When user modify is successful, ensure that further function is
        called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3user_provider = S3UsersProvider("users", "handling users")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3user_provider._handle_success(
                SsplHlProviderS3Users_list.user_list_response, request_mock)
            response_mock.assert_called_once_with(
                SsplHlProviderS3Users_list.user_list_response)
            self.assertEqual(request_mock.reply.call_count, 1)


class SsplHlProviderS3Users_remove(BaseUnitTest):
    def test_execute_command_success(self):
        """Ensure execution of thread based on s3user operation
        request from client.
        """
        request_mock = mock.MagicMock()
        command_args = {
            'command': 'user',
            'action': 'remove',
            'name': 'test',
            'access_key': 'TgVCZxb7TY2wG-ySXVIR1w',
            'secret_key': 'Ihcg/nOEMAVuTB8MQZuUdwDaoAkGdkMhl+AFcd+B'
        }
        request_mock.selection_args = command_args
        s3user_provider = S3UsersProvider("users", "handling users")
        s3user_provider._handle_success = mock.MagicMock()
        with mock.patch("sspl_hl.providers.s3_users.provider.deferToThread",
                        return_value=defer.succeed(
                            SsplHlProviderS3Users_list.user_list_response)):
            with mock.patch('{}.{}.{}'.format("sspl_hl.utils.s3admin",
                                              "user_handler",
                                              "UsersUtility.remove")) \
                    as user_remove_handler_mock:
                s3user_provider.execute_command(request_mock)
                action = request_mock.selection_args.get('action', None)
                self.assertEqual(action, 'remove')
                s3user_provider._handle_success.assert_called_once_with(
                    SsplHlProviderS3Users_list.user_list_response,
                    request_mock)

    def test_handle_modify_success(self):
        """ When user remove is successful, ensure that further function is
        called to process the recived response from s3 server.
        """
        request_mock = mock.MagicMock()
        s3user_provider = S3UsersProvider("users", "handling users")
        with mock.patch('{}.{}.{}'.format(
                "sspl_hl.utils", "message_utils",
                "S3CommandResponse.get_response_message")) \
                as response_mock:
            s3user_provider._handle_success(
                SsplHlProviderS3Users_list.user_list_response, request_mock)
            response_mock.assert_called_once_with(
                SsplHlProviderS3Users_list.user_list_response
            )
            self.assertEqual(request_mock.reply.call_count, 1)


if __name__ == '__main__':
    unittest.main()
