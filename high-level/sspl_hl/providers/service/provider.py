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
