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
# _author_ = Bhupesh Pant

# Third party
import json
import urllib
import subprocess
from plex.util.list_util import ensure_list
from twisted.internet.defer import DeferredList
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from twisted.internet.threads import deferToThread


class StatusProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
    Handler for all status based commands
    """
    CSMAN_CMD = '/usr/local/bin/csman.sh'

    def __init__(self, title, description):
        super(StatusProvider, self).__init__(title, description)
        self.valid_arg_keys = ["command", "debug"]
        self.no_of_arguments = 2
        self.valid_commands = ["ipmi"]
        self.mandatory_args = ["command"]
        self.cluster_state = self.POWER_ON
        self.response_list = {'sem_status': None,
                              'power_status': None,
                              'file_system_status': None}

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

        defer_list = DeferredList(
            [defer_1, defer_2], consumeErrors=True
        )

        defer_list.addCallback(self._process_all_response, request)

    def _process_all_response(self, resp, request):
        """
        Process the status response from all the sources
        """
        if len(resp) != 2:
            err_msg = 'Could not process the response for status command'
            self.log_warning(err_msg)
            request.responder.reply_exception(err_msg)
        else:
            if resp[0][0]:
                self.response_list['power_status'] = resp[0][1]
            else:
                self.log_warning('Failed to get nodes power status')
            if resp[1][0]:
                self.response_list['sem_status'] = resp[1][1]
            else:
                self.log_warning('Failed to get RAS Sem notifications')
            request.reply(ensure_list(self.response_list))

    def get_ras_sem_status(self):
        """
        Gets ras sem notifications
        """
        resp_sem = "Unable to fetch the response of SEM"
        sem = subprocess.Popen(['sh', self.CSMAN_CMD],
                               stdout=subprocess.PIPE)
        resp_sem = sem.communicate()[0] or\
            resp_sem
        return resp_sem

    def handle_success(self, result):
        """
        Success handler for power status
        """
        if not (len(result.get('active_nodes')) or
                len(result.get('inactive_nodes'))):
            self.log_warning(
                'Could not retrieve power status information from cluster'
            )
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
        ssu_nodes = StatusProvider.get_ssu_list()
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
        response = urllib.urlopen(query).read()
        if response:
            try:
                return json.loads(response)
            except ValueError:
                return []
        else:
            return []


# pylint: disable=invalid-name
provider = StatusProvider("status", "Provider for status command")
# pylint: enable=invalid-name
