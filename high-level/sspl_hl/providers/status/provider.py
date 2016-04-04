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
import json
import urllib
import subprocess
from plex.util.list_util import ensure_list
from twisted.internet.defer import DeferredList
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from twisted.internet.threads import deferToThread
from sspl_hl.utils.message_utils import FileSystemStatusQueryRequest
from sspl_hl.utils.rabbit_mq_utils import HalondPublisher


class StatusProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
    Handler for all status based commands
    """

    def __init__(self, title, description):
        super(StatusProvider, self).__init__(title, description)
        self.valid_arg_keys = ["command", "debug"]
        self.no_of_arguments = 2
        self.valid_commands = ["ipmi"]
        self.mandatory_args = ["command"]
        self.cluster_state = self.POWER_ON
        self.publisher = None
        self.response_list = {'sem_status': None,
                              'power_status': None,
                              'file_system_status': None}

    @staticmethod
    def _generate_fs_status_req_msg():
        """ Generate a file system status request message from halon.
        """
        message = FileSystemStatusQueryRequest().get_request_message(
            "cluster", None
        )
        return message

    @staticmethod
    def resp_callback_func(result):
        """ Callback function for defer to receiver query
        """
        if result:
            return result
        else:
            return "No results: EOM"

    @staticmethod
    def resp_err_func(error):
        """ Errback function for defer to receiver.query
        """
        return error

    def callback_func(self, result):
        """ Callback function for defer to publish_fs_status_req
        """
        receiver = self.create_data_receiver(
            app_name='sspl_hl',
            provider_name='response')
        message_id = result.get('message').get('messageId')
        defer_4 = receiver.query({'messageId': message_id})
        defer_4.addCallback(StatusProvider.resp_callback_func)
        defer_4.addErrback(StatusProvider.resp_err_func)
        return defer_4

    def render_query(self, request):
        """
        Handles all the status request issued by the client.
        """
        if not super(StatusProvider, self).render_query(request):
            return

        defer_1 = deferToThread(
            StatusProvider.get_node_power_status
        )
        defer_1.addCallback(self.handle_success)
        defer_1.addErrback(self.handle_failure)
        defer_2 = deferToThread(self.get_ras_sem_status)

        defer_3 = deferToThread(self.publish_fs_status_req)

        defer_3.addCallback(self.callback_func)

        defer_list = DeferredList(
            [defer_1, defer_2, defer_3], consumeErrors=True
        )

        defer_list.addCallback(self._process_all_response, request)

    def publish_fs_status_req(self):
        """ Publish status request message to rabbitmq
        """
        message = self._generate_fs_status_req_msg()
        self.publisher = HalondPublisher(None)
        self.publisher.publish_message(message)
        return message

    def _process_all_response(self, resp, request):
        """
        Process the status response from all the sources
        """
        if len(resp) != 3:
            err_msg = 'Could not process the response for status command.'
            self.log_warning('{} {}'.format(
                err_msg,
                'The response list is not populated correctly.'
            ))
            request.responder.reply_exception(err_msg)
        else:
            # Handle power response
            if resp[0][0]:
                self.response_list['power_status'] = resp[0][1]
            else:
                self.response_list['power_status'] = \
                    dict(active_nodes=[], inactive_nodes=[])
                self.log_warning('Failed to get nodes power status')
            # Handle RAS SEM response
            if resp[1][0]:
                self.response_list['sem_status'] = resp[1][1]
            else:
                self.response_list['sem_status'] = \
                    'Failed to get RAS Sem notifications'
                self.log_warning('Failed to get RAS Sem notifications')
            # Handle File System Status response
            if resp[2][0]:
                self.response_list['file_system_status'] = resp[2][1]
            else:
                self.response_list['sem_status'] = \
                    'Failed to get File System Status'
                self.log_warning('Failed to get File System Status from HAlon')
            request.reply(ensure_list(self.response_list))

    def get_ras_sem_status(self):
        """
        Gets ras sem notifications
        """
        ras_sem_query = 'csman service notifications show'
        try:
            ras_resp = subprocess.check_output(ras_sem_query.split())
        except subprocess.CalledProcessError:
            ras_resp = "Unable to fetch the response of RAS SEM notification"
            self.log_warning('{}. Command Failed: {}'.
                             format(ras_resp, ''.join(ras_sem_query)))
        self.log_debug('RAS SEM notification response: {}'.format(ras_resp))
        return ras_resp

    def handle_success(self, result):
        """
        Success handler for power status
        """
        if not (len(result.get('active_nodes')) or
                len(result.get('inactive_nodes'))):
            self.log_warning(
                'Could not retrieve power status information from cluster'
            )
        self.log_debug('Node Power status response: {}'.format(result))
        return result

    def handle_failure(self, error):
        """
        Error Handler
        """
        self.log_warning(
            'Error occurred in getting the power status of the cluster. '
            'Details: {}'.format(error)
        )

    @staticmethod
    def get_node_power_status():
        """
        Return the power status response
        """
        ssu_nodes_list = StatusProvider.get_ssu_list()
        ssu_nodes = StatusProvider.get_ssu_domain(ssu_nodes_list)
        try:
            active_ssu_list = subprocess.check_output(
                'mco ping -F role=storage',
                shell=True
            )
        except subprocess.CalledProcessError:
            active_ssu_list = ''
        active_ssu_node =\
            [j.strip()
             for i in active_ssu_list.split('\n')
             for j in i.split()
             if j.find('ssu') > -1]

        inactive_ssu_nodes = list(set(ssu_nodes) - set(active_ssu_node))
        power_status_response = dict(active_nodes=active_ssu_node,
                                     inactive_nodes=inactive_ssu_nodes)
        return power_status_response

    @staticmethod
    def get_ssu_list():
        """
        Return the names of all the ssu nodes
        """
        ssu_info = StatusProvider.query_ssu_data_from_puppet()
        ssu_list = []
        for info in ssu_info:
            name = info.get('name')
            if name:
                ssu_list.append(name)
        return ssu_list

    @staticmethod
    def query_ssu_data_from_puppet():
        """
        Make http query to puppet for ssu information
        """
        v3_nodes_url = "http://localhost:8082/v3/nodes"
        query_params = {'query': '["=", ["fact", "role"], "storage"]'}
        query = '{}?{}'.format(v3_nodes_url, urllib.urlencode(query_params))
        try:
            response = urllib.urlopen(query).read()
            return json.loads(response)
        except (ValueError, IOError):
            return []

    @staticmethod
    def get_ssu_domain(ssu_nodes_list):
        """
        Make http query to puppet for ssu domain information
        """
        node_domain_list = []
        for node in ssu_nodes_list:
            query = 'http://localhost:8082/v3/nodes/{}/facts/fqdn'.format(node)
            res = urllib.urlopen(query).read()
            response = json.loads(res)
            response = response and response[-1]
            node_certname = response.get('value', None)
            if node_certname:
                node_domain_list.append(node_certname)
        return node_domain_list


# pylint: disable=invalid-name
provider = StatusProvider("status", "Provider for status command")
# pylint: enable=invalid-name
