"""
Provider for handling user authentication
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
from zope.interface import implements
from twisted.plugin import IPlugin
from twisted.internet import reactor
# PLEX
from plex.util.concurrent.single_thread_executor import SingleThreadExecutor
from plex.common.interfaces.idata_provider import IDataProvider
from plex.core.provider.data_store_provider import DataStoreProvider
# Local
from sspl_hl.utils.access_utils import AccessUtils


class AccessProvider(DataStoreProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """Data Provider"""
    implements(IPlugin, IDataProvider)

    def __init__(self, name, description):
        """
        Prepares list of valid arguments and creates access object
        based on authentication method
        """
        super(AccessProvider, self).__init__(name, description)
        self._single_thread_executor_obj = SingleThreadExecutor()
        self.valid_arg_keys = ['username', 'password']
        self.no_of_arguments = 2
        self.access_config = AccessUtils.get_access_object()

    # pylint: disable=too-many-arguments,unused-argument
    def query(self,
              uri,
              columns,
              selection_args,
              sort_order,
              range_from,
              range_to,
              responder):
        """Query for data.
        @query_selection_args Used to specify arguments for the query.
        It is recommended to use uri over selection args
        @query_sort_order specify the sort order for the data
        """
        self._single_thread_executor_obj.submit(self._query,
                                                selection_args,
                                                responder)

    def _query(self, selection_args, responder):
        """
        Handles user login using username and password
        If valid returns a unique token otherwise return empty message
        @param selection_args:  A dictionary that must contain
                                'command','subcommand',
                                'username' and 'password'.
        @return:                This method will return
                                a token if user is valid otherwise
                                an empty message
                                a record as per given query
        @rtype:                 JSON
        """
        validate_result = self._validate_args(selection_args)
        message = None
        if validate_result:
            message = "Missing argument"
            reactor.callFromThread(responder.reply_exception, validate_result)
            return
        else:
            message = self.access_config.login_user(selection_args['username'],
                                                    selection_args['password'])

        reactor.callFromThread(responder.reply, data=[message])
        return

    def _validate_args(self, selection_args):
        """
        Check selection args contains valid arg keys
        """
        for key in self.valid_arg_keys:
            if key not in selection_args:
                return(
                    "Error: Invalid request: Missing param {}".format(key)
                )
        if len(selection_args) > self.no_of_arguments:
            for key in self.valid_arg_keys:
                del selection_args[key]
            return(
                "Error: Invalid request: Extra param '{extra}' detected"
                .format(extra=selection_args.keys()[0])
            )
        return None

# pylint: disable=invalid-name
provider = AccessProvider("Access", "Provider for authentication")
# pylint: enable=invalid-name, duplicate-code
