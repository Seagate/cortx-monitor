#!/usr/bin/python3

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

#################################################################
# This script performs following operations.
# - Creates datapath as defined in /etc/sspl.conf
# - Check dependencies for roles other than '<product>'
#################################################################

import pwd
import errno

from cortx.utils.conf_store import Conf
from files.opt.seagate.sspl.setup.setup_error import SetupError
from files.opt.seagate.sspl.setup.setup_logger import logger
from framework.base import sspl_constants as consts
from framework.utils.utility import Utility


class SSPLInit:
    """Setup SSPL post cluster configuration."""

    name = "sspl_init"

    def __init__(self):
        """Initialize variables for sspl init."""
        self.user = "sspl-ll"
        Conf.load(consts.SSPL_CONFIG_INDEX, consts.sspl_config_path)

    def validate(self):
        """Check for below requirement.

        1. Validate if sspl-ll user exists
        2. Validate input keys
        """
        # Check sspl-ll user exists
        sspl_uid = Utility.get_uid(self.user)
        if sspl_uid == -1:
            msg = "User %s doesn't exit. Please add user." % self.user
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        # Check input/provisioner configs
        machine_id = Utility.get_machine_id()
        cluster_id = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>cluster_id" % machine_id)
        Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "cluster>%s>name" % cluster_id)
        Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "cluster>%s>site_count" % cluster_id)
        storage_set_count = int(Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "cluster>%s>site>storage_set_count" % cluster_id))
        for i in range(storage_set_count):
            Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "cluster>%s>storage_set[%s]>name" % (cluster_id, i))
            Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "cluster>%s>storage_set[%s]>server_nodes" % (cluster_id, i))
            Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
                "cluster>%s>storage_set[%s]>storage_enclosures" % (cluster_id, i))

    def process(self):
        """Update sspl config."""
        Conf.set(consts.SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_copy_url",
            consts.global_config_path)
        Conf.save(consts.SSPL_CONFIG_INDEX)
