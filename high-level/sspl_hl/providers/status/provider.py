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
    IPMI_COMMAND = "sudo -u plex /usr/local/bin/ipmitooltool.sh"
    IPMI_STATUS_TMP_PATH = "/tmp/ipmi_status.tmp"

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
        try:
            cmd_args = "{} {} > {}".format(
                StatusProvider.IPMI_COMMAND,
                "status",
                StatusProvider.IPMI_STATUS_TMP_PATH
            )
            subprocess.call(cmd_args.split())
            resp = self._read_status_data(StatusProvider.IPMI_STATUS_TMP_PATH)
        except (OSError, ValueError) as process_error:
            reactor.callFromThread(responder.reply_exception,
                                   str(process_error))
        responder.reply(data=[resp])

    @staticmethod
    def _read_status_data(file_name):
        """"""
        try:
            status_f = open(file_name)
            resp = status_f.read()
        except IOError:
            resp = "Unable to fetch the response"
        return resp

# pylint: disable=invalid-name
provider = StatusProvider("status", "Provider for status command")
# pylint: enable=invalid-name
