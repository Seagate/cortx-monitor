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


# Third party
from twisted.internet import reactor
import subprocess
# Local
from sspl_hl.utils.base_castor_provider import BaseCastorProvider


class PowerProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
        Handler for all power based commands
    """

    def __init__(self, name, description):
        super(PowerProvider, self).__init__(name, description)
        self.valid_arg_keys = ['command', 'debug']
        self.no_of_arguments = 2
        self.valid_commands = ['on', 'off']
        self.mandatory_args = ['command']
        self._ipmi_cmds = {'on': 'poweron',
                           'off': 'poweroff'}

    def _query(self, selection_args, responder):
        """ Sets state of power on the cluster.

        This generates a json message and places it into rabbitmq where it will
        be processed by halond and eventually sent out to the various nodes in
        the cluster and processed by sspl_hl.

        @param selection_args:    A dictionary that must contain 'target'
                                  and 'command' the command should be one
                                  of ''on', 'off' and 'status'
                                  and nodes value could be a regex indicating
                                  which nodes to operate on, eg
                                  'mynode0[0-2]'
        """
        result = super(PowerProvider, self)._validate_params(selection_args)
        if result:
            reactor.callFromThread(responder.reply_exception, result)
            return
        ret_val = -1
        ipmitool_command = self._ipmi_cmds.get(
            selection_args['command'], selection_args['command'])
        try:
            ret_val = subprocess.call(["ipmitooltool.sh", ipmitool_command])
        except OSError as process_error:
            reactor.callFromThread(responder.reply_exception,
                                   str(process_error))
        else:
            if ret_val is not 0:
                # report error:
                pass

        reactor.callFromThread(responder.reply, ret_val)

# pylint: disable=invalid-name
provider = PowerProvider("power", "Provider for power command")
# pylint: enable=invalid-name
