"""
PLEX data provider for service implementation.
"""
# Third party
from twisted.internet import reactor

# Local
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from sspl_hl.utils.message_utils import ServiceListResponse
from sspl_hl.utils.message_utils import ServiceQueryRequest


class ServiceProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """ Used to set state of services on the cluster. """

    def __init__(self, name, description):
        super(ServiceProvider, self).__init__(name, description)
        self.no_of_arguments = 3
        self.valid_arg_keys = ['serviceName', 'command', 'debug']

    @staticmethod
    def _generate_service_request_msg(
            service_name,
            command):
        """ Generate a service request message.

        @param service_name:      Name of the service, eg 'crond.service'.
        @param command:           Operation.  Must be one of 'start', 'stop',
                                  'restart', 'enable', 'disable', 'status'.
        @param now:               The current time.  (iso formatted).
        @return:                  json service request message.
        @rtype:                   json
        """
        message = ServiceQueryRequest().get_request_message(
            service_name,
            command)
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
            reactor.callFromThread(responder.reply_exception, result)
            return

        message = None
        if selection_args['command'] in ['list']:
            list_response = ServiceListResponse()
            message = list_response.get_response_message()
        else:
            message = self._generate_service_request_msg(
                service_name=selection_args['serviceName'],
                command=selection_args['command']
                )

            self._publish_message(message)

        if message and selection_args['debug'] == 'True' \
                or selection_args['command'] in ['list']:
            reactor.callFromThread(responder.reply, data=[message])
        else:
            reactor.callFromThread(responder.reply_no_match)

# pylint: disable=invalid-name
provider = ServiceProvider("service", "Service Management Provider")
# pylint: enable=invalid-name
