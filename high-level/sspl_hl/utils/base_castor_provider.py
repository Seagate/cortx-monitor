"""
Implements the base class for all the castor cli providers
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

from plex.common.interfaces.idata_provider import IDataProvider
from twisted.plugin import IPlugin
from plex.core.provider.data_store_provider import DataStoreProvider
from zope.interface import implements


class BaseCastorProvider(DataStoreProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    # pylint: disable=too-many-instance-attributes
    """
    Base class for each provider
    """
    implements(IPlugin, IDataProvider)

    POWER_STATUS_CONFIG_FILE = "./power_status.json"
    POWER_ON = 1
    POWER_OFF = 2

    def __init__(self,
                 title,
                 description,
                 style=DataStoreProvider.THREAD_STYLE.NON_REACTOR):

        super(BaseCastorProvider, self).__init__(title=title,
                                                 description=description,
                                                 thread_style=style)
        self._connection = None
        self._channel = None
        self.valid_commands = []
        self.valid_subcommands = []
        self.mandatory_args = []
        self.no_of_arguments = 1
        self.valid_arg_keys = []

    def render_query(self, request):
        """
        It is the base class version of the render query. Actual
        implementations would be in their respective providers.
        """
        result = self._validate_params(selection_args=request.selection_args)
        if result:
            self.log_warning(result)
            request.responder.reply_exception(result)
            return False
        return True

    def _validate_params(self, selection_args):
        """ ensure query() parameters are ok. """
        val_result = self._validate_supported_args(selection_args)
        if val_result:
            return val_result
        val_result = \
            self._validate_supported_commands(selection_args['command'])
        if val_result:
            return val_result
        if 'subcommand' in selection_args:
            val_result = \
                self._validate_supported_subcommands(
                    selection_args['subcommand']
                )
        return val_result

    def _validate_supported_args(self, selection_args):
        """
        Validate the supplied arguments should one of the supported args only.
        """
        val_result = self._validate_supported_args_count(selection_args)
        if val_result:
            return val_result
        val_result = self._validate_mandatory_args(selection_args)
        if val_result:
            return val_result
        ret_val = self._validate_unsupported_args(selection_args)
        return ret_val

    def _validate_unsupported_args(self, selection_args):
        """
        Check if the args are from supported list
        """
        for arg_key in selection_args:
            if arg_key not in self.valid_arg_keys:
                return(
                    "Error: Invalid request: Unsupported args {}".
                    format(arg_key)
                    )

    def _validate_supported_commands(self, command):
        """
        validate the command from the list of supported commands.
        """
        if command not in self.valid_commands:
            return(
                "Error: Invalid command: '{}'".format(
                    command
                    )
                )

    def _validate_supported_subcommands(self, sub_command):
        """
        validate the subcommand from the list of supported subcommands.
        """
        if sub_command not in self.valid_subcommands:
            return(
                "Error: Invalid subcommand: '{}'".format(
                    sub_command
                    )
                )

    def _validate_supported_args_count(self, selection_args):
        """
        Validate supported args count and report any extra param.
        """
        # if len(selection_args) < self.no_of_arguments:
        #     return('Invalid Request: Minimum number of arguments needed'
        #            ' for this request is not supplied.')
        if len(selection_args) > self.no_of_arguments:
            dict_clone = selection_args.copy()
            for arg_key in self.valid_arg_keys:
                del dict_clone[arg_key]
            return("Error: Invalid request: Extra parameter"
                   " '{extra}' detected"
                   .format(extra=dict_clone.keys()[0]))

    def _validate_mandatory_args(self, selection_args):
        """
        Validate all the mandatory args in the selection arguments.
        """
        for args in self.mandatory_args:
            if args not in selection_args:
                return("Error: Invalid request: Missing mandatory args: {}".
                       format(args))
