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

BASE_BUCKET_PATH = '/var/lib/support_bundles'
NODES_ACCESS_KEY = 'dcouser'
PLEX_LOGS = 'plex_logs'
LOCAL = 'local'
REMOTE = 'remote'
BUCKET = 'bucket'
FILES = 'files'
ACTION = 'action'
MISC = 'misc'

SUPPORT_BUNDLE_DIR_STRUCTURE = {"nodes": {}, "logs": {}, PLEX_LOGS: {}}

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
#                     E.g. {"mero": [list of mero files to be collected ]}
#                     This would collect all the mero logs mentioned
#                     to the mero directory inside bundle.
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
# Common params are as follows:
# A). COMMON_ACTION_FOR_CMU_SSU   B). COMMON_FILES_TO_COLLECT_CMU_SSU
#
# LOCAL PARAMS: Configuration params that is specific to local nodes only.
# Local params are as follows,
# A). ACTION_TO_TRIGGER_ON_LOCAL_NODE  B). LOCAL_FILES_TO_COLLECT
# C). MISC_LOCAL_FILES_MAPPING
#
# REMOTE PARAMS: Configuration params that is specific to Remote nodes.
# Remote params are as follows,
# ACTION_TO_TRIGGER_ON_REMOTE_NODE
# REMOTE_FILES_TO_COLLECT

# """
# COMMON SUBSET PARAMS
# """
COMMON_ACTION_FOR_CMU_SSU = [
    'm0reportbug',
    'm0addb2dump',
    'mv -f m0reportbug-data.tar.gz /tmp/bundle/',
    'mv -f m0trace.* /tmp/bundle/',
    'dmesg > /tmp/bundle/dmesg.log'
]

COMMON_FILES_TO_COLLECT_CMU_SSU = [
    '/var/log/audit/audit.log',
    '/var/crash/*'
]

# """
# REMOTE CONFIGURATION
# """
ACTION_TO_TRIGGER_ON_REMOTE_NODE = [
    'm0reportbug',
    'mv -f m0reportbug-data.tar.gz /tmp/bundle/',
]

REMOTE_FILES_TO_COLLECT = [

]

# """
# LOCAL CONFIGURATION
# """
ACTION_TO_TRIGGER_ON_LOCAL_NODE = [

] + COMMON_ACTION_FOR_CMU_SSU

LOCAL_FILES_TO_COLLECT = [
    '/etc/sysconfig/mero',
    '/etc/mero/*',
    '/var/log/messages',
    '/tmp/bundle/m0reportbug-data.tar.gz',
    '/tmp/bundle/dmesg.log',
    '/tmp/bundle/m0trace*',
    '/run/log/journal/*'
] + COMMON_FILES_TO_COLLECT_CMU_SSU

MISC_LOCAL_FILES_MAPPING = {
    PLEX_LOGS: ['/var/log/plex/plex*']
}
