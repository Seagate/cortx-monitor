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

from plex.util.list_util import ensure_list
from plex.util.shell_command import ShellCommand
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.cluster_node_manager.cluster_node_information \
    import ClusterNodeInformation


class PowerProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
    Handler for all power based commands
    """

    IPMI_CMD = "sudo /usr/local/bin/ipmitooltool.sh"

    def __init__(self, title, description, cluster_node_information_class):
        super(PowerProvider, self).__init__(title=title,
                                            description=description)
        self.valid_arg_keys = ['command', 'debug']
        self.no_of_arguments = 2
        self.valid_commands = ['on', 'off']
        self.mandatory_args = ['command']
        self._ipmi_cmds = {'on': 'poweron',
                           'off': 'poweroff'}
        self._shell_command = ShellCommand()
        self._cluster_node_information_class = cluster_node_information_class

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
        state_cluster, nodes_list = self._cluster_node_information_class.\
            get_cluster_state_info()
        if state_cluster == 'up' and \
                request.selection_args.get('command') == 'on':
            reply_msg = 'Nodes are already powered on. ' \
                        '\nPlease use ' \
                        '\'status\' command to check ' \
                        'the power status of nodes.'
            self.log_info(reply_msg)
            request.reply(ensure_list({'power_commands_reply': reply_msg}))
        elif state_cluster == 'down' and \
                request.selection_args.get('command') == 'off':
            reply_msg = 'Nodes are already powered off. ' \
                        '\nPlease use ' \
                        '\'status\' command to check ' \
                        'the power status of nodes.'
            self.log_info(reply_msg)
            request.reply(ensure_list({'power_commands_reply': reply_msg}))
        else:
            # pylint: disable=no-member
            deferred = self._shell_command.run_command(cmd_args)
            # pylint: disable=no-member
            deferred.addCallback(self._handle_success_power_cmd, request,
                                 state_cluster, nodes_list)
            # pylint: disable=no-member
            deferred.addErrback(self._handle_failure_power_cmd, request)

    def _handle_success_power_cmd(self, ipmi_response, request,
                                  cluster_state, nodes_list):
        """
        Success handler for ShellCommand.run_command()
        """
        # todo: This will be done as separate task
        reply_msg = ''
        if request.selection_args.get('command') == 'on':
            reply_msg = self._reply_msg_for_poweron(cluster_state,
                                                    nodes_list)
        elif request.selection_args.get('command') == 'off':
            reply_msg = self._reply_msg_for_poweroff(cluster_state,
                                                     nodes_list)
        self.log_info('IPMI RESPONSE --> {}'.format(ipmi_response))
        self.log_info(reply_msg)
        request.reply(ensure_list({'power_commands_reply': reply_msg}))

    def _handle_failure_power_cmd(self, failure, request):
        """
        Error handler for ShellCommand.run_command()
        """
        self.log_warning("Unable to execute the command: {}".
                         format(failure.getErrorMessage()))
        request.responder.reply_exception(failure.getErrorMessage())

    @staticmethod
    def _reply_msg_for_poweron(cluster_state, nodes_list):
        reply_msg = ''
        inactive_nodes = nodes_list.get('inactive_nodes', [])
        inactive_nodes = '\n'.join(inactive_nodes)

        if cluster_state == 'down':
            reply_msg = 'Cluster Power on has been ' \
                        'initiated on all the nodes. ' \
                        '\nPlease use ' \
                        '\'status\' command to check the ' \
                        'power status of nodes.'
        elif cluster_state == 'partially_up':
            reply_msg = 'Cluster Power on has been ' \
                        'initiated on following nodes:\n' \
                        '{}\nPlease use ' \
                        '\'status\' command to check the power ' \
                        'status of nodes.'\
                        .format(inactive_nodes)
        return reply_msg

    @staticmethod
    def _reply_msg_for_poweroff(cluster_state, nodes_list):
        reply_msg = ''
        active_nodes = nodes_list.get('active_nodes', [])
        active_nodes = '\n'.join(active_nodes)
        if cluster_state == 'up':
            reply_msg = 'Cluster Power off has been ' \
                        'initiated on all the nodes. ' \
                        '\nPlease use ' \
                        '\'status\' command to check the ' \
                        'power status of nodes.'
        elif cluster_state == 'partially_up':
            reply_msg = 'Cluster Power off has been ' \
                        'initiated on following nodes:\n' \
                        '{}\nPlease use ' \
                        '\'status\' command to check the power ' \
                        'status of nodes.'\
                        .format(active_nodes)

        return reply_msg

# pylint: disable=invalid-name
provider = PowerProvider("power", "Provider for power command",
                         ClusterNodeInformation)
# pylint: enable=invalid-name
