"""
Status provider implementation
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


class StatusProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
    Handler for all status based commands
    """

    def __init__(self, name, description):
        super(StatusProvider, self).__init__(name, description)
        self.valid_arg_keys = ["command", "debug"]
        self.no_of_arguments = 2
        self.valid_commands = ["ipmi"]
        self.mandatory_args = ["command"]

    def _query(self, selection_args, responder):
        """
        """
        result = super(StatusProvider, self)._validate_params(selection_args)
        if result:
            reactor.callFromThread(responder.reply_exception, result)
            return
        resp = "Unable to fetch the response"
        try:
            cmd_args = "{} {}".format(
                BaseCastorProvider.IPMI_CMD,
                "status"
            )
            resp = subprocess.Popen(
                cmd_args.split(),
                stdout=subprocess.PIPE).communicate()[0] or\
                resp

        except (OSError, ValueError) as process_error:
            reactor.callFromThread(responder.reply_exception,
                                   str(process_error))
        responder.reply(data=[resp])

# pylint: disable=invalid-name
provider = StatusProvider("status", "Provider for status command")
# pylint: enable=invalid-name
