"""
File containing "Power provider", handling of the power sub-commands
"""

# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# from plex.core.provider.dac.file_data_source import FileDataSource
from plex.util.list_util import ensure_list
from plex.util.shell_command import ShellCommand
from sspl_hl.utils.base_castor_provider import BaseCastorProvider


class PowerProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
    Handler for all power based commands
    """

    IPMI_CMD = "/usr/local/bin/ipmitooltool.sh"

    def __init__(self, title, description):
        super(PowerProvider, self).__init__(title=title,
                                            description=description)
        self.valid_arg_keys = ['command', 'debug']
        self.no_of_arguments = 2
        self.valid_commands = ['on', 'off']
        self.mandatory_args = ['command']
        self._ipmi_cmds = {'on': 'poweron',
                           'off': 'poweroff'}
        self._shell_command = ShellCommand()

    def render_query(self, request):
        """
        Handles all the power request issued by the client.
        """
        if not super(PowerProvider, self).render_query(request):
            return
        selection_args = request.selection_args
        ipmitool_command = self._ipmi_cmds.get(
            selection_args['command'], selection_args['command'])
        cmd_args = "{} {}".format(PowerProvider.IPMI_CMD, ipmitool_command)
        # pylint: disable=no-member
        deferred = self._shell_command.run_command(cmd_args)
        # pylint: disable=no-member
        deferred.addCallback(self._handle_success_power_cmd, request)
        # pylint: disable=no-member
        deferred.addErrback(self._handle_failure_power_cmd, request)
        return deferred

    def _handle_success_power_cmd(self, _, request):
        """
        Success handler for ShellCommand.run_command()
        """
        # todo: This will be done as separate task
        # power_info_file = FileDataSource(
        #     BaseCastorProvider.POWER_STATUS_CONFIG_FILE
        # )
        # power_status_info = {'status': request.selection_args['command']}
        # deferred = power_info_file.write(power_status_info)
        # deferred.addCallback(self.handle_success)
        # deferred.addErrback(self.handle_failure)

        reply_msg = 'Cluster Power \'{}\' has been initiated. Please use ' \
                    '\'status\' command to check the power status of nodes.'\
                    .format(request.selection_args.get('command'))
        self.log_info(reply_msg)
        request.reply(ensure_list({'power_commands_reply': reply_msg}))

    def _handle_failure_power_cmd(self, failure, request):
        """
        Error handler for ShellCommand.run_command()
        """
        self.log_warning("Unable to execute the command: {}".
                         format(failure.getErrorMessage()))
        request.responder.reply_exception(failure.getErrorMessage())

# pylint: disable=invalid-name
provider = PowerProvider("power", "Provider for power command")
# pylint: enable=invalid-name
