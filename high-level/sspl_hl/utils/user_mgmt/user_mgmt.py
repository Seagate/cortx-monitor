# Copyright (c) 2017 Seagate Technology LLC and/or its Affiliates
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

"""Module that maintains the user management interface"""


import plex.core.log as plex_log
from sspl_hl.utils.command_executor import RootCommandExecutor
from sspl_hl.utils.user_mgmt.access_permission import AccessPermission


class UserMgmt(object):
    """User management class handles all the operations related to user
    management. For e.g.
    1. User add/remove
    3. User configure
    4. User disable/enable
    All the operations will be carried out by POSIX libraries.
    """

    def __init__(self, logger=plex_log):
        self.logger = logger

    def create_user(self, user):
        """Handles Creation of new user using POSIX commands"""
        USER_ADD = 'useradd {}'
        if not user.username or not user.pwd:
            return dict(ret_code=1,
                        output='Username OR password is not supplied '
                               'for create_user()')
        user_add_cmd = USER_ADD.format(user.username, user.pwd)
        cmd_executor = RootCommandExecutor(user_add_cmd)
        try:
            ret = cmd_executor.run()
            self.logger.debug('User mgmt command,{} executed, result: {}'.
                              format(user_add_cmd, ret))
            return dict(ret_code=ret.get('ret_code'), output=ret.get('output'))
        except Exception as err:
            self.logger.warning('Error Occurred in create_user called with'
                                ' : {}. Details: {}'.format(user, str(err)))
            return dict(ret_code=1, output=str(err))

    def configure_user(self, user):
        """Configures the user, username for groups mentioned in components"""
        USER_SET_PWD = 'echo {} | passwd {} --stdin'
        if not user.username or not user.pwd:
            return dict(ret_code=1,
                        output='Username is not supplied for configure_user()')

        user_config_cmd = USER_SET_PWD.format(user.pwd, user.username)
        cmd_executor = RootCommandExecutor(user_config_cmd)
        try:
            ret = cmd_executor.run()
            self.logger.debug('User mgmt command,{} executed, result: {}'.
                              format(user_config_cmd, ret))
            response = dict(ret_code=ret.get('ret_code'),
                            output=ret.get('output'))
        except Exception as err:
            self.logger.warning('Unknown Error Occurred while Configuring '
                                'User. Param Details: [{}]. Error : {}'
                                .format(user, str(err)))
            return dict(ret_code=1, output=str(err))

        # Give the requested permission to the new user
        for comp in user.authorizations:
            perm = AccessPermission.get_object(comp)
            ret = perm.grant_permission(user)
            if ret.get('ret_code') > 0:
                self.logger.warning('Permission Grant Failed for: {}'.format(
                    comp))
                return ret
        self.logger.debug('Permission Granted Successfully on: {} for user: '
                          '[{}]'.format(user.authorizations, user.username))
        response['ret_code'] = 0
        return response

    def remove_user(self, user):
        """Handles removal of user in node using POSIX commands"""
        USER_REM = 'userdel --remove {}'
        if not user.username:
            return dict(ret_code=1,
                        output='Username is not supplied for remove_user()')
        user_rem_cmd = USER_REM.format(user.username)
        cmd_executor = RootCommandExecutor(user_rem_cmd)
        try:
            ret = cmd_executor.run()
            self.logger.debug('User mgmt command,{} executed, result: {}'.
                              format(user_rem_cmd, ret))
            return dict(ret_code=ret.get('ret_code'), output=ret.get('output'))
        except Exception as err:
            self.logger.warning(
                'Remove user command failed. User: {}. Details:{}'.format(
                    user.username, str(err))
            )
            return dict(ret_code=1, output=str(err))


# user = User(username='bhanu', pwd='bhanu123',
#             authorizations=['ras', 'halon', 'apache'])
# ret = UserMgmt().configure_user(user)
# obj = AccessPermission.get_object('ras')
# print obj.grant_permission(user)
