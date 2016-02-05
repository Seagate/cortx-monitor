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
import json
import urllib
from plex.util.list_util import ensure_list
import subprocess
from sspl_hl.utils.base_castor_provider import BaseCastorProvider
from twisted.internet.threads import deferToThread


class StatusProvider(BaseCastorProvider):
    # pylint: disable=too-many-ancestors,too-many-public-methods
    """
    Handler for all status based commands
    """

    def __init__(self, name, description):
        super(StatusProvider, self).__init__(name, description)
        self.valid_arg_keys = ["command", "debug"]
        self.no_of_arguments = 2
        self.valid_commands = ["ipmi"]
        self.mandatory_args = ["command"]

    def _query(self, selection_args, responder):
        """
        """
        result = super(StatusProvider, self)._validate_params(selection_args)
        if result:
            responder.reply_exception(ensure_list(result))
            return
        deferred_power_status = deferToThread(
            StatusProvider.get_node_power_status
        )
        deferred_power_status.addCallback(
            self.handle_success,
            responder
        )
        deferred_power_status.addErrback(
            self.handle_failure,
            responder
        )

    def handle_success(self, result, responder):
        """
        Success handler for power status
        """
        if not (len(result.get('active_nodes')) or
                len(result.get('inactive_nodes'))):
            self.log_warning(
                'Could not fetch the data from mco for power status'
            )
            responder.reply_exception(
                'Could not retrieve power status information from cluster')
        else:
            responder.reply(ensure_list(result))

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
