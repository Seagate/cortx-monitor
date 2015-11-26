"""
    It will contains the following information for each node,
    files: files to collect,
    action: command to run,
    bucket: information of the directory in the center server that
    will store the bundle collected from the node.
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

import os
from sspl_hl.utils.support_bundle import config
from sspl_hl.utils.support_bundle.config import \
    ACTION, LOCAL, REMOTE, BUCKET, FILES, MISC

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

    def __init__(self, cluster_info, bucket):
        self._base_bucket = \
            os.path.join(config.BASE_BUCKET_PATH, bucket)
        self._collection_rules = \
            self._generate_rules(cluster_info)

    def _generate_rules(self, cluster_info):
        """
        Create a dict of collection rules for the cluster.
        Please refer the message structure above.
        """

        default_remote = {
            ACTION: config.ACTION_TO_TRIGGER_ON_REMOTE_NODE,
            FILES: config.REMOTE_FILES_TO_COLLECT,
            BUCKET: ''
        }
        misc_files_rules = self._get_misc_files_rules()

        default_local = {
            ACTION: config.ACTION_TO_TRIGGER_ON_LOCAL_NODE,
            FILES: config.LOCAL_FILES_TO_COLLECT,
            BUCKET: os.path.join(self._base_bucket, 'logs'),
            MISC: misc_files_rules
        }
        rules = {}
        remote = {}
        for node in cluster_info:
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
        return self._collection_rules[LOCAL]

    def get_remote_files_info(self):
        """
        Return remote file collection rules.
        """
        return self._collection_rules[REMOTE]
