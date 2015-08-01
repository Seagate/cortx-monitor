"""
PLEX data provider for service implementation.
"""
# Third party
from twisted.internet import reactor
import json
import datetime
import uuid
# PLEX
# Local

from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.message_utils import ServiceListResponse


class ServiceProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """ Used to set state of services on the cluster. """

    def __init__(self, name, description):
        super(ServiceProvider, self).__init__(name, description)
        self.valid_arg_keys = ['serviceName', 'command']

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
        result = super(ServiceProvider, self)._query(selection_args, responder)
        if result:
            reactor.callFromThread(responder.reply_exception(result))
            return

        if selection_args['command'] in ['list', 'status']:
            list_response = ServiceListResponse()
            service_list = list_response.get_response_message()
            reactor.callFromThread(responder.reply(data=[service_list]))
        else:
            message = self._generate_service_request_msg(
                service_name=selection_args['serviceName'],
                command=selection_args['command'],
                )

            self._publish_message(message)

            reactor.callFromThread(responder.reply_no_match)


# pylint: disable=invalid-name
provider = ServiceProvider("service", "Service Management Provider")
# pylint: enable=invalid-name
