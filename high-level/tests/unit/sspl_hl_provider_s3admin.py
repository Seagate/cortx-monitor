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

""" Unit tests for sspl_hl.providers.s3auth.provider """

import unittest
from sspl_hl.providers.s3admin.provider import S3AdminProvider
from sspl_hl.providers.s3_account.provider import S3AccountProvider
from base_unit_test import BaseUnitTest
from twisted.internet import defer
import mock


# pylint: disable=too-many-public-methods
class SsplHlProvidersS3admin(BaseUnitTest):
    """ Test methods of the
        sspl_hl.providers.s3admin.provider.S3AdminProvider object.
    """

    def test_invalid_command(self):
        """ Ensure s3admin undefined/invalid subcommand generates
        an exception and can not proceed further.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'invalid_command', 'action': 'create',
                        'name': 'UT_Test', 'email': 'ut@test.com'}
        request_mock.selection_args = command_args
        s3admin_provider = S3AdminProvider("s3admin",
                                           "Provider for s3admin commands")
        s3admin_provider.render_query(request_mock)
        self.assertEqual(request_mock.responder.reply_exception.call_count, 1)

    def test_render_query(self):
        """ Ensure s3admin command request is received, is processed and
        directed towards respective further process.
        """
        request_mock = mock.MagicMock()
        s3admin_provider = S3AdminProvider("s3admin",
                                           "Provider for s3admin commands")
        s3admin_provider.process_s3admin_request = mock.MagicMock()
        s3admin_provider.render_query(request_mock)
        s3admin_provider.process_s3admin_request.assert_called_once_with(
            request_mock)

    def test_process_s3admin_request(self):
        """Ensure s3admin subcommand request is received and get sorted
        on the basis of parameter 'command' and directed towards respective
        provider.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'account', 'action': 'create',
                        'name': 'UT_Test', 'email': 'ut@test.com'}
        request_mock.selection_args = command_args
        s3admin_provider = S3AdminProvider("s3admin",
                                           "Provider for s3admin commands")
        s3admin_provider.handle_account_command = mock.MagicMock()
        s3admin_provider.process_s3admin_request(request_mock)
        command = request_mock.selection_args.get('command', None)
        self.assertEqual(command, 'account')
        s3admin_provider.handle_account_command.assert_called_once_with(
            request_mock)

    def test_handle_account_command(self):
        """Ensure s3admin account subcommand request
        is processed and directed towards respective provider.
        """
        request_mock = mock.MagicMock()
        command_args = {'command': 'account', 'action': 'create',
                        'name': 'UT_Test', 'email': 'ut@test.com'}
        request_mock.selection_args = command_args
        s3admin_provider = S3AdminProvider("s3admin",
                                           "Provider for s3admin commands")
        with mock.patch('{}.{}.{}'.format("sspl_hl.providers",
                                          "s3_account.provider",
                                          "S3AccountProvider.handleRequest")) \
                as s3account_provider:
            s3admin_provider.handle_account_command(request_mock)
            self.assertEqual(s3account_provider.call_count, 1)


if __name__ == '__main__':
    unittest.main()
