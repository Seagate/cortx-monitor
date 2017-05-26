"""
Support Bundle handler. It will,
1). Do all the necessary pre-requisite set up for bundling.
    1.1) Preparing the necessary directory structure in the local system
    1.2) Communication with SSUs.l
2). Prepare the bundling data.
    2.1) It includes generation of m0reportbug data
3). Set all the bundling logic.
    3.1) bundle all the target data into a single tar bundle
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

from sspl_hl.utils.cluster_node_manager.cluster_node_information import \
    ClusterNodeInformation
from sspl_hl.utils.support_bundle import bundle_utils
from sspl_hl.utils.support_bundle.file_collector.\
    cluster_files_collection_rules import \
    ClusterFilesCollectionRules
from sspl_hl.utils.support_bundle import config
from sspl_hl.utils.support_bundle.file_collector.file_collector import \
    LocalFileCollector, \
    McoRemoteFileCollector
import os
from sspl_hl.utils.common import execute_shell
from plex.util.concurrent.executor_safe import ExecutorSafe, executorSafe
from plex.util.concurrent.single_thread_executor import SingleThreadExecutor
import plex.core.log as logger


class SupportBundleHandler(ExecutorSafe):
    """
    Support Bundle handler. It will,
    1). Do all the necessary pre-requisite set up for bundling.
        1.1) Preparing the necessary directory structure in the local system
        1.2) Communication with SSUs.l
    2). Prepare the bundling data.
        2.1) It includes generation of m0reportbug data
    3). Set all the bundling logic.
        3.1) bundle all the target data into a single tar bundle
    """

    def __init__(self):
        super(SupportBundleHandler, self).__init__(SingleThreadExecutor())
        self._cluster_node_manger = ClusterNodeInformation()
        self._file_collection_rules = None
        self._ssu_list = []

    @executorSafe
    def collect(self, bundle_name):
        # todo: collection info parameter should be added.
        """
        Collect all the logs of the mero cluster system.
        @:param collection_info (YET TO BE ADDED ): json in
        the following format:
        {"message": "Could be reason for the collection",
         "time": "time_in_utc_format",
         "owner": "Default_for_now",
         "no_delete": "Indication to not delete this bundle",
         "name":"Same as the tar bar name"
        }
        """
        logger.debug('Collection of bundle files has Started')
        self._ssu_list = self._cluster_node_manger.get_active_nodes()
        logger.info('SSU List : {}'.format(self._ssu_list))
        bundle_dir_info = bundle_utils.get_bundle_dir_config(
            config.SUPPORT_BUNDLE_DIR_STRUCTURE,
            self._ssu_list,
            bundle_name
        )
        logger.info('Bundle_dir_info : {}'.format(bundle_dir_info))
        bundle_utils.create_bundle_structure(
            config.BASE_BUCKET_PATH,
            bundle_dir_info
        )

        self._file_collection_rules = \
            ClusterFilesCollectionRules(self._ssu_list,
                                        self._cluster_node_manger.
                                        get_cmu_hostname(),
                                        bundle_name)
        logger.info('Bundling Info: Bundle_id: {}, Collection_rule: {}'.
                    format(bundle_name,
                           self._file_collection_rules.get_remote_files_info())
                    )
        self.collect_files_from_cluster()
        SupportBundleHandler.build_tar_bundle(bundle_dir_info)
        logger.info('Collection of bundle files has Successfully completed. '
                    'Bundle ID: {}'.format(bundle_name))
        return 'success'

    def collect_files_from_cluster(self):
        """
        Collect files from local and remote cluster
        """

        SupportBundleHandler.collect_remote_files(
            self._file_collection_rules.get_remote_files_info()
        )

        SupportBundleHandler.collect_local_files(
            self._file_collection_rules.get_local_files_info()
        )

    @staticmethod
    def build_tar_bundle(bundle_dir_info):
        """
        Build the tar ball of the complete bundle.
        """
        bundle_name = bundle_dir_info.keys()[0]
        bundle_path = os.path.join(config.BASE_BUCKET_PATH, bundle_name)
        bundle_cmd = 'tar -cf {}/{}.tar -C {} {}'.format(
            config.BASE_BUCKET_PATH,
            bundle_name,
            config.BASE_BUCKET_PATH,
            bundle_name
        )
        execute_shell(bundle_cmd)
        rm_cmd = 'rm -rf {}'.format(bundle_path)
        execute_shell(rm_cmd)

    @staticmethod
    def collect_remote_files(collection_rules):
        """
        This will contain the actual implementation of collecting the
        files from remote hosts. All the collection is based on the remote
        collection rules. Collection will be handled by RemoteFileCollector
        object.
        """
        file_collector = McoRemoteFileCollector(collection_rules)
        file_collector.collect()

    @staticmethod
    def collect_local_files(collection_rules):
        """"
        Collect the local files using LocalFileCollector object.
        """
        file_collector = LocalFileCollector('local', collection_rules)
        file_collector.collect()
