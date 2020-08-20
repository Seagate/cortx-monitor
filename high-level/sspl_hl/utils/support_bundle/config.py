"""
Contains the configuration used by the support bundle module.
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

from sspl_hl.utils.halon import HalonConfigurationPuppet

BASE_BUCKET_PATH = '/var/lib/support_bundles'
NODES_ACCESS_KEY = 'dcouser'
PLEX_LOGS = 'plex_logs'
LOCAL = 'local'
REMOTE = 'remote'
BUCKET = 'bucket'
FILES = 'files'
ACTION = 'action'
MISC = 'misc'
CLEANUP = 'cleanup'

# The temporary directory created during the bundling. It will be deleted
#  as a part of cleanup.
BUNDLE_TMP_DIR = '/tmp/bundle/'

SUPPORT_BUNDLE_DIR_STRUCTURE = {"nodes": {}, "logs": {}, PLEX_LOGS: {}}


def get_decision_logs_command():
    """Query Halon interface and get the decision log node
     and Path"""
    cnf = HalonConfigurationPuppet()
    cmd = 'scp root@{}:{} {}'.format(
        cnf.get_station_node_info(),
        cnf.get_decision_logs_path(),
        BUNDLE_TMP_DIR
    )
    if 'DUMMY' in cmd:
        return 'echo "Decision Logs could not be collected"'
    return cmd


def get_halon_logs_path():
    """"""
    cnf = HalonConfigurationPuppet()
    return cnf.get_decision_logs_path()


# """
# Enable ssu_log_collector.py logging. A new bundle.log file will be added
# in the support_bundle/nodes/xxxxx/ dir, which will contain the debug
# level information remote bundling.
# """
TRACE_ENABLED_SSU_BUNDLING = True

#
#                     ** BUNDLING CONFIGURATION Params **
#
# Bundling Configurations param is divided into two category,
#
# 1. Local bundling Params
#     | --> ACTIONS : List of commands to be executed on local nodes
#     | --> FILE    : List of files to be copied from localhost
#     | --> MISC    : Contains the dictionary of files that
#                     needs to be collected but put to some
#                     specific folders inside bundle package.
#                     E.g. {"motr": [list of motr files to be collected ]}
#                     This would collect all the motr logs mentioned
#                     to the motr directory inside bundle.
#    | --> CLEANUP  : List of all the commands for cleaning up the
#                     tmp files. (NOTE: Yet to be added)
#
# 2. Remote bundling Params
#     | --> ACTIONS : List of commands to be executed on remote nodes
#     | --> FILE    : List of files to be copied from remote nodes
#     | --> CLEANUP : List of all the commands for cleaning up the
#                      tmp files. (NOTE: Yet to be added)
#
#              ** CONFIGURATION PARAMS SEGREGATION **
#
#                       (Common Params)
#                              |
#                ______________|_______________
#                |                            |
#                |                            |
#          (Local Params)               (Remote Params)
#
# COMMON PARAMS:  Configuration params common to both Local and remote nodes of
#                 Cluster  are moved to common params. If any action of files
#                 needs to be executed or collected respectively then put it to
#                  common configuration.
#
#  Common params are as follows:
# A). COMMON_ACTION_FOR_CMU_SSU
# B). COMMON_FILES_TO_COLLECT_CMU_SSU
# C). CLEANUP_CODE
#
# LOCAL PARAMS: Configuration params that is specific to local nodes only.
# Local params are as follows,
# A). ACTION_TO_TRIGGER_ON_LOCAL_NODE
# B). LOCAL_FILES_TO_COLLECT
# C). MISC_LOCAL_FILES_MAPPING
#
# REMOTE PARAMS: Configuration params that is specific to Remote nodes.
# Remote params are as follows,
# A). ACTION_TO_TRIGGER_ON_REMOTE_NODE
# B). REMOTE_FILES_TO_COLLECT

# """
# COMMON SUBSET PARAMS
# """
COMMON_ACTION_FOR_CMU_SSU = [
    'dmesg > {}'.format(os.path.join(BUNDLE_TMP_DIR, 'dmesg.log'))
]

COMMON_FILES_TO_COLLECT_CMU_SSU = [
    '/var/log/audit/audit.log',
    '/var/crash/*'
]


COMMON_CLEANUP = [BUNDLE_TMP_DIR]

# """
# REMOTE CONFIGURATION
# """
ACTION_TO_TRIGGER_ON_REMOTE_NODE = [
    'm0reportbug',
    'mv -f m0reportbug-data.tar.gz {}'.format(BUNDLE_TMP_DIR),
    'mv -f m0reportbug-traces.tar.gz {}'.format(BUNDLE_TMP_DIR),
    'mv -f m0reportbug-cores.tar.gz {}'.format(BUNDLE_TMP_DIR),
] + COMMON_ACTION_FOR_CMU_SSU

REMOTE_FILES_TO_COLLECT = [
    '{}'.format(get_halon_logs_path())
] + COMMON_FILES_TO_COLLECT_CMU_SSU

REMOTE_CLEANUP = [] + COMMON_CLEANUP

# """
# LOCAL CONFIGURATION
# """
ACTION_TO_TRIGGER_ON_LOCAL_NODE = [
    'sudo m0reportbug',
    ] + COMMON_ACTION_FOR_CMU_SSU

LOCAL_FILES_TO_COLLECT = [
    '/etc/sysconfig/motr',
    '/etc/motr/*',
    '/var/log/messages',
    '{}'.format(os.path.join(BUNDLE_TMP_DIR, 'm0reportbug-data.tar.gz')),
    '{}'.format(os.path.join(BUNDLE_TMP_DIR, 'm0reportbug-traces.tar.gz')),
    '{}'.format(os.path.join(BUNDLE_TMP_DIR, 'm0reportbug-cores.tar.gz')),
    '{}'.format(os.path.join(BUNDLE_TMP_DIR, 'dmesg.log')),
    '/run/log/journal/*'
] + COMMON_FILES_TO_COLLECT_CMU_SSU

MISC_LOCAL_FILES_MAPPING = {
    PLEX_LOGS: ['/var/log/plex/plex*']
}

LOCAL_CLEANUP = [] + COMMON_CLEANUP
