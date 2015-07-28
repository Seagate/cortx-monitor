"""
PLEX data provider for service implementation.
"""
# Third party
from twisted.internet import reactor
import pika
import json
import datetime
import uuid
# PLEX
# Local

from plex.util.concurrent.single_thread_executor import SingleThreadExecutor
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.message_utils import ServiceListResponse


class Provider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """ Used to set state of services on the cluster. """

    def __init__(self, name, description):
        super(Provider, self).__init__(name, description)
        self._single_thread_executor = SingleThreadExecutor()
        self._connection = None
        self._channel = None

    def on_create(self):
        self._single_thread_executor.submit(self._on_create)

    def _on_create(self):
        """ Implement this method to initialize the Provider. """

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

    @staticmethod
    def _validate_params(selection_args, responder):
        """ Ensure query() parameters are ok. """
        valid_commands = [
            'start', 'stop', 'restart', 'enable', 'disable', 'status', 'list'
            ]
        if 'serviceName' not in selection_args:
            reactor.callFromThread(responder.reply_exception(
                "Error: Invalid request: Missing serviceName"
                ))
            return False
        elif 'command' not in selection_args:
            reactor.callFromThread(responder.reply_exception(
                "Error: Invalid request: Missing command"
                ))
            return False
        elif selection_args['command'] not in valid_commands:
            reactor.callFromThread(responder.reply_exception(
                "Error: Invalid command: '{}'".format(
                    selection_args['command']
                    )
                ))
            return False
        elif len(selection_args) > 2:
            del selection_args['command']
            del selection_args['serviceName']
            reactor.callFromThread(responder.reply_exception(
                "Error: Invalid request: Extra parameter '{extra}' detected"
                .format(extra=selection_args.keys()[0])
                ))
            return False

        return True

    @staticmethod
    def _generate_service_request_msg(
            service_name,
            command,
            now=datetime.datetime.utcnow().isoformat() + '+00:00'):
        """ Generate a service request message.

        @param service_name:      Name of the service, eg 'crond.service'.
        @param command:           Operation.  Must be one of 'start', 'stop',
                                  'restart', 'enable', 'disable', 'status'.
        @param now:               The current time.  (iso formatted).
        @return:                  json service request message.
        @rtype:                   json
        """
        message = """
            {{
                "username": "ignored_for_now",
                "signature": "None",
                "time": "{now}",
                "expires": 3600,
                "message":
                {{
                    "messageId": "{messageId}",
                    "serviceRequest":
                    {{
                        "serviceName": "{serviceName}",
                        "command": "{command}"
                    }}
                }}
            }}
            """
        message = message.format(
            messageId=uuid.uuid4(),
            serviceName=service_name,
            command=command,
            now=now,
            )
        message = json.loads(message)
        return message

    def _query(self, selection_args, responder):
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
        if selection_args['command'] in ['list']:
            list_response = ServiceListResponse()
            service_list = list_response.get_response_message()
            reactor.callFromThread(responder.reply(data=[service_list]))
        else:
            message = self._generate_service_request_msg(
                service_name=selection_args['serviceName'],
                command=selection_args['command'],
                )

            self._channel.basic_publish(
                exchange='sspl_hl_cmd',
                routing_key='sspl_hl_cmd',
                body=json.dumps(message)
                )
            reactor.callFromThread(responder.reply_no_match)


# pylint: disable=invalid-name
provider = Provider("service", "Service Management Provider")
# pylint: enable=invalid-name
