"""
It will handle all the cluster/node related operations.
Common responsibility includes,
1. Discovery of all the nodes or only SSUs in the cluster.
2. Communication with any/all the nodes in the cluster.
"""
# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2015 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# __author__ = 'Bhupesh Pant'
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
