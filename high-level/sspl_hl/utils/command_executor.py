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

"""Module that handles execution of commands in the cluster.
CommandExecutor: handles execution of any command w/o sudo priviliges
whereas,
RootCommandExecutor: handles the execution with root priviliges.
"""


import subprocess
import plex.core.log as plex_log


class CommandExecutor(object):
    """This class will provide an interface for command executor."""

    def __init__(self, command):
        self.command = command
        self.result = dict(cmd=command, ret_code=0, output='')

    def run(self):
        """The command will be executed using subprocess module
        Returns a dict containing the information about the execution
        status.

        ret_code : // Contains the status return value //
        output :  // output of the command that is redirected to stdio //
        cmd :  // Command that was executed by CommandExecutor //
        """
        try:
            plex_log.debug('Command: {} will be executed'.format(self.command))
            output = subprocess.check_output(self.command, shell=True)
            self.result = dict(cmd=self.command, ret_code=0, output=output)
            plex_log.debug('Command: {} executed. Status: {}'.format(
                self.command, self.result)
            )
        except subprocess.CalledProcessError as err:
            self.result = dict(cmd=self.command,
                               ret_code=err.returncode,
                               output=err.output)
            plex_log.warning('Command,{} execution Failed. Details: {}'.
                             format(self.command, str(err)))
        return self.result

    def get_ret_code(self):
        """Returns the return code of the executed command"""
        return self.result.get('ret_code')

    def get_output(self):
        """Returns the output of the executed command"""
        return self.result.get('output')


class RootCommandExecutor(CommandExecutor):
    """This class will provide an interface for command executor for
    executing the commands as root.  This execution will be handled by
    mco at the implementation level but triggered by subprocess.
    So in a way we will wrap a mco command over user's command"""

    def __init__(self, command):
        mco_cmd = 'mco rpc runcmd rc cmd=\"{}\" -F role=cc'. \
            format(command)
        super(RootCommandExecutor, self).__init__(mco_cmd)

    def run(self):
        """Execute the command as root."""
        return super(RootCommandExecutor, self).run()
