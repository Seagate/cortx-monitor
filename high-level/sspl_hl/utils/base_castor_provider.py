""" uitls
"""
# Third party
import pika
import json

from plex.util.concurrent.single_thread_executor import SingleThreadExecutor
from plex.common.interfaces.idata_provider import IDataProvider
from twisted.plugin import IPlugin
from plex.core.provider.data_store_provider import DataStoreProvider
from zope.interface import implements


class BaseCastorProvider(DataStoreProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """ Used to set state of ha on the cluster. """
    implements(IPlugin, IDataProvider)

    def __init__(self, name, description):
        super(BaseCastorProvider, self).__init__(name, description)
        self._single_thread_executor = SingleThreadExecutor()
        self._connection = None
        self._channel = None
        self.valid_commands = ['start',
                               'stop',
                               'restart',
                               'enable',
                               'disable',
                               'list',
                               'status']
        self.valid_subcommands = []
        self.no_of_arguments = 2
        self.valid_arg_keys = []

    # pylint: disable=too-many-arguments
    def query(self,
              uri,
              columns,
              selection_args,
              sort_order,
              range_from,
              range_to,
              responder):
        self._single_thread_executor.submit(self._query,
                                            selection_args,
                                            responder)

    # pylint: disable=unused-argument
    def _query(self, selection_args, responder):
        return self._validate_params(selection_args)

    def on_create(self):
        self._single_thread_executor.submit(self._on_create)

    def _on_create(self):
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host='localhost',
                virtual_host='SSPL',
                credentials=pika.PlainCredentials('sspluser', 'sspl4ever')
                )
            )
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange='sspl_hl_cmd', type='topic', durable=False
            )

    def _publish_message(self, message):
        self._channel.basic_publish(exchange='sspl_hl_cmd',
                                    routing_key='sspl_hl_cmd',
                                    body=json.dumps(message))

    def _validate_params(self, selection_args):
        """ ensure query() parameters are ok. """
        for arg_key in self.valid_arg_keys:
            if arg_key not in selection_args:
                return(
                    "Error: Invalid request: Missing {}".format(arg_key)
                    )
        if selection_args['command'] not in self.valid_commands:
            return(
                "Error: Invalid command: '{}'".format(
                    selection_args['command']
                    )
                )
        if ('action' in selection_args and
                len(selection_args) == self.no_of_arguments + 1):
            if selection_args['action'] == 'ha':
                if selection_args['subcommand'] not in self.valid_subcommands:
                    return(
                        "Error: Invalid subcommand: '{}'".format(
                            selection_args['subcommand']
                            )
                        )
            del selection_args['action']
        if len(selection_args) > self.no_of_arguments:
            for arg_key in self.valid_arg_keys:
                del selection_args[arg_key]
            return(
                "Error: Invalid request: Extra parameter '{extra}' detected"
                .format(extra=selection_args.keys()[0])
                )
        return None
