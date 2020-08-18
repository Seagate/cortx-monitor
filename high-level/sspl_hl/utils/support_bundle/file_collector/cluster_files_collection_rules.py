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
    It will contains the following information for each node,
    files: files to collect,
    action: command to run,
    bucket: information of the directory in the center server that
    will store the bundle collected from the node.
"""

import os
from sspl_hl.utils.support_bundle import config
from sspl_hl.utils.support_bundle.config import \
    ACTION, LOCAL, REMOTE, BUCKET, FILES, MISC, \
    REMOTE_CLEANUP, CLEANUP, LOCAL_CLEANUP

# Message structure of cluster_file_collection_rules:
# {
# 'local': {
#         'action': [List of commands],
#         'files': [List of files],
#         'bucket':'',
#         'misc': {
#             'bucket_1': [List of files],
#             'bucket_2': [List of files],
#         },
#         'cleanup': [List of commands]
#     },
# 'remote': {
#         "node_1": {
#             'action': [List of commands],
#             'files': [List of files],
#             'bucket':'',
#             'cleanup': [List of commands]
#         },
#         "node_2": {
#             'action': [List of commands],
#             'files': [List of files],
#             'bucket':'',
#             'cleanup': [List of commands]
#         },
#         "node_3": {
#             'action': [List of commands],
#             'files': [List of files],
#             'bucket':'',
#             'cleanup': [List of commands]
#         },
#     }
# }
# cleanup attribute will be added later on! Currently its hardcoded


class ClusterFilesCollectionRules(object):
    """
    It will contains the following information for each node,
    files: files to collect,
    action: command to run,
    bucket: information of the directory in the center server that
    will store the bundle collected from the node.
    """

    def __init__(self, ssu_list, cmu_hostname, bucket):
        self._cmu_hostname = cmu_hostname
        self._base_bucket = \
            os.path.join(config.BASE_BUCKET_PATH, bucket)
        self._collection_rules = \
            self._generate_rules(ssu_list)

    def _generate_rules(self, ssu_list):
        """
        Create a dict of collection rules for the cluster.
        Please refer the message structure above.
        """
        # defaut_host: It will contains the information about
        # the host details like,
        # 1. hostname
        # 2. pwd to connect to host
        # 3. Bucket on the host to send files.
        default_host = {
            'name': self._cmu_hostname,
            'viel': config.NODES_ACCESS_KEY,
            BUCKET: os.path.join(self._base_bucket, 'nodes/')
        }

        default_remote = {
            ACTION: config.ACTION_TO_TRIGGER_ON_REMOTE_NODE,
            FILES: config.REMOTE_FILES_TO_COLLECT,
            BUCKET: '',
            'host': default_host,
            CLEANUP: REMOTE_CLEANUP

        }
        misc_files_rules = self._get_misc_files_rules()

        default_local = {
            ACTION: config.ACTION_TO_TRIGGER_ON_LOCAL_NODE,
            FILES: config.LOCAL_FILES_TO_COLLECT,
            BUCKET: os.path.join(self._base_bucket, 'logs'),
            MISC: misc_files_rules,
            CLEANUP: LOCAL_CLEANUP
        }
        rules = {}
        remote = {}
        for node in ssu_list:
            remote[node] = dict(default_remote)
            remote[node][BUCKET] = \
                os.path.join(self._base_bucket, 'nodes', '{}/'.format(node))
        rules[REMOTE] = remote
        rules[LOCAL] = default_local
        return rules

    def _get_misc_files_rules(self):
        """
        create the misc files collection rules.
        """
        misc_files = config.MISC_LOCAL_FILES_MAPPING
        return \
            {os.path.join(self._base_bucket, key): misc_files[key]
             for key in misc_files}

    def get_local_files_info(self):
        """
        Return local file collection rules.
        """
        return self._collection_rules.get(LOCAL)

    def get_remote_files_info(self):
        """
        Return remote file collection rules.
        """
        return self._collection_rules.get(REMOTE)
