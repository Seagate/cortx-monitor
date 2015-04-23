"""
PLEX data provider.
"""
# Third party
from zope.interface import implements
from twisted.plugin import IPlugin
import pika
import json
# PLEX
from plex.common.interfaces.idata_provider import IDataProvider
from plex.core.provider.data_store_provider import DataStoreProvider
# Local


class Provider(DataStoreProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """ Used to set state of services on the cluster. """
    implements(IPlugin, IDataProvider)

    def __init__(self, name, description):
        super(Provider, self).__init__(name, description)
        self._connection = None
        self._channel = None

    def on_create(self):
        """ Implement this method to initialize the Provider. """
        self._connection = pika.BlockingConnection(
            pika.ConnectionParameters(host='localhost')
            )
        self._channel = self._connection.channel()
        self._channel.exchange_declare(
            exchange='sspl_hl_cmd', type='topic', durable=True
            )

    @staticmethod
    def _validate_params(selection_args, responder):
        """ Ensure query() parameters are ok. """
        valid_commands = [
            'start', 'stop', 'restart', 'enable', 'disable', 'status'
            ]
        if 'serviceName' not in selection_args:
            responder.reply_exception(
                "Error: Invalid request: Missing serviceName"
                )
            return False
        elif 'command' not in selection_args:
            responder.reply_exception(
                "Error: Invalid request: Missing command"
                )
            return False
        elif selection_args['command'] not in valid_commands:
            responder.reply_exception(
                "Error: Invalid command: '{}'".format(
                    selection_args['command']
                    )
                )
            return False
        elif len(selection_args) > 2:
            del selection_args['command']
            del selection_args['serviceName']
            responder.reply_exception(
                "Error: Invalid request: Extra parameter '{extra}' detected"
                .format(extra=selection_args.keys()[0])
                )
            return False

        return True

    def query(
            self, uri, columns, selection_args, sort_order,
            range_from, range_to, responder
            ):  # pylint: disable=too-many-arguments
        """ Sets state of services on the cluster.

        This generates a json message and places it into rabbitmq where it will
        be processed by halond and eventually sent out to the various nodes in
        the cluster and processed by sspl-ll.

        @param selection_args:    A dictionary that must contain 'serviceName'
                                  and 'command' keys, and can optionally
                                  include a 'nodes' key.  The serviceName
                                  should be the service in question (ie crond),
                                  the command should be one of 'start', 'stop',
                                  'restart', 'enable', 'disable', or 'status',
                                  and nodes value should be a regex indicating
                                  which nodes to operate on, eg
                                  'mycluster0[0-2]'
        """
        if not self._validate_params(selection_args, responder):
            return

        message = json.loads("""
            {{
                "serviceRequest":
                {{
                    "serviceName": "{serviceName}",
                    "command": "{command}"
                }}
            }}
            """.format(
            serviceName=selection_args['serviceName'],
            command=selection_args['command'])
            )

        self._channel.basic_publish(
            exchange='sspl_hl_cmd',
            routing_key='sspl_hl_cmd',
            body=json.dumps(message)
            )
        responder.reply_no_match()


# pylint: disable=invalid-name
provider = Provider("service", "Service Management Provider")
# pylint: enable=invalid-name
