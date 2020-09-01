# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

"""
It will handle all the cluster/node related operations.
Common responsibility includes,
1. Discovery of all the nodes or only SSUs in the cluster.
2. Communication with any/all the nodes in the cluster.
"""
import json
import subprocess
import urllib
import plex.core.log as logger


class ClusterNodeInformation(object):
    # pylint: disable=too-few-public-methods
    """
    It will handle all the cluster/node related operations.
    Common responsibility includes,
    1. Discovery of all the nodes or only SSUs in the cluster.
    2. Communication with any/all the nodes in the cluster.
    """
    @staticmethod
    def get_ssu_list():
        """
        Return the list of all SSUs in the cluster.
        """
        ssu_list = []
        query = urllib.urlencode(
            {'query': '["=", ["fact", "role"], "storage"]'}
        )
        try:
            resp = urllib.urlopen(
                'http://localhost:8082/v3/nodes?{}'.format(query)
                )
        except IOError:
            return []
        for node_name in json.loads(resp.read()):
            if node_name:
                ssu_list.append(node_name)
        return ssu_list

    @staticmethod
    def get_active_nodes():
        """
        Returns all the active nodes in the cluster
        """
        mco_ping = 'mco find -F role=storage'
        try:
            ssu_list = subprocess.check_output(
                mco_ping, shell=True
            ).split()
            logger.debug('Active SSUs from command, {} : - {}'.format(
                mco_ping,
                ssu_list))
            return ssu_list
        except subprocess.CalledProcessError as err:
            logger.warning(
                'Failed to get SSU list. Details: {}'.format(str(err))
            )
            return []

    @staticmethod
    def get_cmu_hostname():
        """
        Get hostname of the CMU
        """
        try:
            return subprocess.check_output('hostname').strip()
        except subprocess.CalledProcessError:
            return ''

    def get_node_power_status(self):
        """
        Return the power status response
        """
        ssu_nodes_list = self.get_ssu_name_list()
        ssu_nodes = self.get_ssu_domain(ssu_nodes_list)
        active_ssu_nodes = self.get_active_nodes()
        inactive_ssu_nodes = list(set(ssu_nodes) - set(active_ssu_nodes))
        power_status_response = dict(active_nodes=active_ssu_nodes,
                                     inactive_nodes=inactive_ssu_nodes)
        return power_status_response

    def get_ssu_name_list(self):
        """
        Return the names of all the ssu nodes
        """
        ssu_info = self.query_ssu_data_from_puppet()
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

    @staticmethod
    def get_cluster_state_info():
        """
        Returns the state of a cluster
        """
        cluster_state = 0
        list_of_nodes = ClusterNodeInformation().get_node_power_status()
        active_nodes = list_of_nodes.get('active_nodes', [])
        inactive_nodes = list_of_nodes.get('inactive_nodes', [])
        if not active_nodes:
            cluster_state = 'down'
        elif not inactive_nodes:
            cluster_state = 'up'
        elif active_nodes and inactive_nodes:
            cluster_state = 'partially_up'
        return cluster_state, list_of_nodes
