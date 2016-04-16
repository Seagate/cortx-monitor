"""
Contains File collector class for remote and local nodes
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
from sspl_hl.utils.cluster_node_manager.node_communication_handler import \
    Node, \
    NodeCommunicationHandler, \
    SSHException
from sspl_hl.utils.support_bundle.config import \
    ACTION, BUCKET, FILES, MISC
from sspl_hl.utils.common import execute_shell
import os
import shutil
import subprocess
import plex.core.log as plex_log


class FileCollector(object):
    # pylint: disable=too-few-public-methods
    """
    Base class of File collector.
    """
    BUNDLE_TMP_DIR = '/tmp/bundle'

    def __init__(self, host, collection_rules, logger=plex_log):
        self.is_log_collected = False
        self.collection_rules = collection_rules
        self._actions = collection_rules.get(ACTION, [])
        self._files = collection_rules.get(FILES, [])
        self._bucket = collection_rules.get(BUCKET, '')
        self.host = host
        self.log = logger

    def collect(self):
        """
        Collect the defined Files
        """
        try:
            LocalFileCollector.create_tmp_bundle_directory()
            self._execute_actions()
            self._collect_files()
            self._clean_up()
        except (OSError, IOError):
            # todo: log and exit
            pass

    def _execute_actions(self):
        """
        Execute the actions
        """
        raise NotImplementedError

    def _clean_up(self):
        """
        Do the necessary cleaning, like closing any connections or
        removing the temp files.
        """
        pass

    def _collect_files(self):
        """
        Collect files and put to a common bucket
        """
        pass


class LocalFileCollector(FileCollector):
    """
    Collects files from the local machine
    """

    def __init__(self, host, collection_rules):
        super(LocalFileCollector, self).__init__(host, collection_rules)
        self._misc_files = collection_rules.get(MISC)

    def collect(self):
        """
        Collect the files from local machine
        """
        try:
            LocalFileCollector.create_tmp_bundle_directory()
            self._execute_actions()
            self._collect_files()
            self._clean_up()
        except (OSError, IOError):
            # todo: log and exit
            pass

    def _execute_actions(self):
        """
        Execute the actions
        """
        for action in self._actions:
            try:
                execute_shell(action)
            except (OSError, subprocess.CalledProcessError):
                # todo: Add logging
                pass

    @staticmethod
    def create_tmp_bundle_directory():
        """
        Create bundling tmp directory for local node.
        """
        if os.path.exists(FileCollector.BUNDLE_TMP_DIR):
            os.rmdir(FileCollector.BUNDLE_TMP_DIR)
        os.mkdir(FileCollector.BUNDLE_TMP_DIR)

    def _collect_files(self):
        """
        Collect files from various logging sources to bucket.
        """
        for _file in self._files:
            try:
                if os.path.isfile(_file):
                    shutil.copy(_file, self._bucket)
                else:
                    cp_cmd = 'cp {} {}'.format(_file, self._bucket)
                    execute_shell(cp_cmd)
            except (OSError, IOError, subprocess.CalledProcessError):
                # todo: necessary logging
                pass
        self._collect_misc_files()

    def _collect_misc_files(self):
        """
        Collection of misc files to the respective bucket.
        """
        for bucket in self._misc_files.keys():
            for _file in self._misc_files[bucket]:
                try:
                    if os.path.isfile(_file):
                        shutil.copy(_file, self._bucket)
                    else:
                        cp_cmd = 'cp {} {}'.format(_file, bucket)
                        execute_shell(cp_cmd)
                except (OSError, IOError, subprocess.CalledProcessError):
                    # todo: necessary logging
                    pass

    def _clean_up(self):
        """
        delete the tmp files and folders.
        """
        for _file in [FileCollector.BUNDLE_TMP_DIR]:
            rm_cmd = 'rm -rf {}'.format(_file)
            try:
                execute_shell(rm_cmd)
            except (OSError, subprocess.CalledProcessError):
                # todo: necessary logging
                pass


class RemoteFileCollector(FileCollector):
    # pylint: disable=too-few-public-methods
    """
    Collects files from the Remote machine
    """

    def __init__(self, host, collection_rules):
        super(RemoteFileCollector, self).__init__(host, collection_rules)
        self._channel = NodeCommunicationHandler(
            Node(host)
        )

    def collect(self):
        """
        Collect the bundle from the cluster
        """
        try:
            self._channel.establish_connection()
            self._channel.open_ftp_channel()
            self._execute_actions()
            self._collect_files()
            self._clean_up()
            self._channel.close_connection()
        except (SSHException, IOError) as extra_info:
            # todo: Necessary logging
            print 'Error occurred during remote file collection. Details: {}'\
                .format(str(extra_info))

    def _collect_files(self):
        """
        Collect files from remote nodes and copy it to bucket
        """
        remote_file = '{}bundle.tar'.format(self._bucket)
        self._create_bundle_on_remote_host()
        self._channel.get_file('/tmp/bundle.tar', remote_file)

    def _create_bundle_on_remote_host(self):
        """
        Copy each file mentioned in the list to remote bundle package
        """
        tar_cmd = 'tar -cf /tmp/bundle.tar -C /tmp bundle'
        for _file in self._files:
            cp_file_cmd = 'cp {} /tmp/bundle/'.format(_file)
            self._channel.execute_command(cp_file_cmd)
        self._channel.execute_command(tar_cmd)

    def _execute_actions(self):
        """
        Execute the actions
        """
        self._create_tmp_bundle_directory()
        for action in self._actions:
            try:
                self._channel.execute_command(action)
            except SSHException:
                # todo: Log the failure and continue
                pass

    def _create_tmp_bundle_directory(self):
        """
        Create the tmp bundle directory on SSUs
        """
        bundle_tmp_dir = 'mkdir {}'.format(FileCollector.BUNDLE_TMP_DIR)
        try:
            self._channel.execute_command(bundle_tmp_dir)
        except (SSHException, IOError):
            # todo: Take necessary steps
            print 'Unable to create bundle base: {} on host: {}'.format(
                FileCollector.BUNDLE_TMP_DIR,
                self.host
            )
            raise

    def _clean_up(self):
        """Clean all the temp files and the directory"""
        cleanup_files = [FileCollector.BUNDLE_TMP_DIR]
        for _file in cleanup_files:
            rm_cmd = 'rm -rf {}'.format(_file)
            try:
                self._channel.execute_command(rm_cmd)
            except SSHException:
                # todo: necessary logging
                pass


class McoRemoteFileCollector(object):
    # pylint: disable=too-few-public-methods
    """
    MCO interface for the remote file collection.
    """

    MCO_REMOTE_COLLECTION = 'python /var/lib/ssu_logs_collector.py'

    def __init__(self, collection_rules):
        """"""
        collection_rules = collection_rules.values()
        self._node_collection_rule = \
            collection_rules and collection_rules[-1]
        del self._node_collection_rule['bucket']

    def collect(self):
        """
        collect the remote bundling
        """
        plex_log.info('Remote bundling args:- {}'.format(
            self._node_collection_rule))
        self._execute_actions()

    def _execute_actions(self):
        """
        Execute the command on remote node using mco
        """
        rules_node = json.dumps(self._node_collection_rule)
        node_rule = rules_node.replace('"', '\\"')
        command = '{} \'{}\''.format(
            McoRemoteFileCollector.MCO_REMOTE_COLLECTION,
            node_rule
        )
        mco_cmd = 'mco rpc runcmd rc cmd=\"{}\" -F role=storage'.\
            format(command)
        plex_log.info(
            'Sending mco command, {} for initiating bundling '
            'from SSU nodes'.format(mco_cmd)
            )
        try:
            result = subprocess.check_output(mco_cmd, shell=True)
            plex_log.info(
                'Remote bundling is completed with Return code: {}'
                .format(result))
        except (subprocess.CalledProcessError, OSError) as err:
            err_msg = \
                'Command: {}, failed to execute. Details: {}'.format(
                    command,
                    str(err)
                )
            plex_log.warning(err_msg)
            return None
        return result
