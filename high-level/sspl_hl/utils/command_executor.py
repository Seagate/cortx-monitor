"""Module that handles execution of commands in the cluster.
CommandExecutor: handles execution of any command w/o sudo priviliges
whereas,
RootCommandExecutor: handles the execution with root priviliges.
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# __author__ = 'Bhupesh Pant'

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
