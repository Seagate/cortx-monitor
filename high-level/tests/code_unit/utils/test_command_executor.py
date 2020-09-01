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

from sspl_hl.utils.command_executor import CommandExecutor
import unittest
from mock import MagicMock, patch


class TestCommandExecutor(unittest.TestCase):
    """"""
    def setUp(self):
        self.dummy_command = 'Dummy command for testing'

    @patch('sspl_hl.utils.command_executor.subprocess')
    def test_command_exe_run(self, subprocess_mock):
        a_mock = MagicMock()
        a_mock.return_value = 'Execution Successful'
        subprocess_mock.check_output = a_mock
        cmd = CommandExecutor(self.dummy_command)
        cmd.run()
        a_mock.assert_called_once_with(self.dummy_command, shell=True)

    @patch('sspl_hl.utils.command_executor.subprocess')
    def test_command_exe_run_return_dict(self, subprocess_mock):
        a_mock = MagicMock()
        a_mock.return_value = 'Execution Successful'
        subprocess_mock.check_output = a_mock
        cmd = CommandExecutor(self.dummy_command)
        ret_val = cmd.run()
        self.assertTrue(isinstance(ret_val, dict))
        self.assertEquals(ret_val.get('cmd'), self.dummy_command)
        self.assertEqual(ret_val.get('ret_code'), 0)

    @patch('sspl_hl.utils.command_executor.subprocess')
    def test_command_exe_run_output(self, subprocess_mock):
        a_mock = MagicMock()
        a_mock.return_value = 'Execution Successful'
        subprocess_mock.check_output = a_mock
        cmd = CommandExecutor(self.dummy_command)
        cmd.run()
        self.assertEquals(cmd.get_output(), 'Execution Successful')

if __name__ == '__main__':
    unittest.main()
