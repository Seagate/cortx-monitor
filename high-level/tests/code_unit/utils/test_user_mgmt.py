import unittest
from mock import patch, Mock
from sspl_hl.utils.user_mgmt.user import User
from sspl_hl.utils.user_mgmt.user_mgmt import UserMgmt


class TestUserMgmt(unittest.TestCase):
    """Test cases for UserMgmt interface"""

    def setUp(self):
        """Creating dummy User object"""
        USER_ADD = 'useradd {} -p $(echo {} | openssl passwd -1 -stdin)'
        USER_REM = 'userdel --remove {}'
        self.user = User(username='Fredie Mercury',
                         pwd='queen',
                         authorizations=['ras'])
        self.user_add_cmd = USER_ADD.format(self.user.username,
                                            self.user.pwd)
        self.user_remove_cmd = USER_REM.format(self.user.username)
        self.user_mgmt_object = UserMgmt()
        self.ret_val = dict(ret_code=666, output='We are the Champions')
        self.a_mock = Mock()
        self.a_mock.run.return_value = self.ret_val

    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_create_user_called(self, u_mgmt_mock):
        u_mgmt_mock.return_value = self.a_mock
        self.user_mgmt_object.create_user(self.user)
        u_mgmt_mock.called_with(self.user_add_cmd)

    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_create_user_ret_code(self, u_mgmt_mock):
        u_mgmt_mock.return_value = self.a_mock
        ret_val = self.user_mgmt_object.create_user(self.user)
        self.assertEqual(666, ret_val.get('ret_code'))

    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_create_user_ret_output(self, u_mgmt_mock):
        u_mgmt_mock.return_value = self.a_mock
        ret_val = self.user_mgmt_object.create_user(self.user)
        self.assertEquals('We are the Champions', ret_val.get('output'))

    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_create_user_username_missing(self, u_mgmt_mock):
        u_mgmt_mock.return_value = self.a_mock
        err_str = 'Username OR password is not supplied for create_user()'
        self.user.username = ''
        ret_val = self.user_mgmt_object.create_user(self.user)
        self.assertEqual(1, ret_val.get('ret_code'))
        self.assertEquals(err_str, ret_val.get('output'))

    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_create_user_pwd_missing(self, u_mgmt_mock):
        err_str = 'Username OR password is not supplied for create_user()'
        u_mgmt_mock.return_value = self.a_mock
        self.user.pwd = ''
        ret_val = self.user_mgmt_object.create_user(self.user)
        self.assertEqual(1, ret_val.get('ret_code'))
        self.assertEquals(err_str, ret_val.get('output'))

#     Remove command test cases:-
    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_remove_user_called(self, u_mgmt_mock):
        u_mgmt_mock.return_value = self.a_mock
        self.user_mgmt_object.remove_user(self.user)
        u_mgmt_mock.called_with(self.user_remove_cmd)

    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_create_user_ret_code(self, u_mgmt_mock):
        u_mgmt_mock.return_value = self.a_mock
        ret_val = self.user_mgmt_object.create_user(self.user)
        self.assertEqual(666, ret_val.get('ret_code'))

    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_remove_user_ret_output(self, u_mgmt_mock):
        u_mgmt_mock.return_value = self.a_mock
        ret_val = self.user_mgmt_object.remove_user(self.user)
        self.assertEquals('We are the Champions', ret_val.get('output'))

    @patch('sspl_hl.utils.user_mgmt.user_mgmt.RootCommandExecutor')
    def test_remove_user_username_missing(self, u_mgmt_mock):
        u_mgmt_mock.return_value = self.a_mock
        err_str = 'Username is not supplied for remove_user()'
        self.user.username = ''
        ret_val = self.user_mgmt_object.remove_user(self.user)
        self.assertEqual(1, ret_val.get('ret_code'))
        self.assertEquals(err_str, ret_val.get('output'))


if __name__ == '__main__':
    unittest.main()
