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
