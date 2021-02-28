#!/bin/env python3

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
# This script performs following operations
# - Check if product is one of the enabled products
# - Configures self.role in sspl.conf if supplied
# - Executes sspl_reinit script
# - Updates cluster nodes passed in cli to consul
#################################################################

import os
import shutil
import re
import errno

# Using cortx package
from cortx.utils.conf_store import Conf
from cortx.utils.message_bus import MessageBus, MessageBusAdmin
from cortx.utils.message_bus.error import MessageBusError
from cortx.utils.process import SimpleProcess
from files.opt.seagate.sspl.setup.setup_error import SetupError
from .conf_based_sensors_enable import update_sensor_info
from framework.base import sspl_constants as consts
from framework.utils.utility import Utility


class SSPLConfig:
    """SSPL setup config interface."""

    name = "config"

    def __init__(self):
        """Initialize varibales for Config stage."""
        self.topic_already_exists = "ALREADY_EXISTS"
        Conf.load(consts.SSPL_CONFIG_INDEX, consts.sspl_config_path)

    def validate(self):
        """Check for below requirement.

        1. Validate input configs
        2. Validate sspl conf is created
        3. Check if message bus is accessible
        """
        if os.geteuid() != 0:
            raise SetupError(errno.EINVAL,
                "Run this command with root privileges.")

        # Validate input/provisioner configs
        machine_id = Utility.get_machine_id()
        Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>cluster_id" % machine_id)
        self.node_type = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>type" % machine_id)
        enclosure_id = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "server_node>%s>storage>enclosure_id" % machine_id)
        self.enclosure_type = Utility.get_config_value(consts.PRVSNR_CONFIG_INDEX,
            "storage_enclosure>%s>type" % enclosure_id)

        # Validate sspl conf is created
        if not os.path.isfile(consts.file_store_config_path):
            raise SetupError(errno.EINVAL,
                "Missing configuration - %s !! Create and rerun.",
                consts.file_store_config_path)

        # Validate message bus is accessible
        self.mb = MessageBus()

    def process(self):
        """Configure sensor monitoring and log level setting."""
        if os.path.isfile(consts.SSPL_CONFIGURED):
            os.remove(consts.SSPL_CONFIGURED)

        os.makedirs(consts.SSPL_CONFIGURED_DIR, exist_ok=True)
        with open(consts.SSPL_CONFIGURED, 'a'):
            os.utime(consts.SSPL_CONFIGURED)
        sspl_uid = Utility.get_uid(consts.USER)
        sspl_gid = Utility.get_gid(consts.USER)
        Utility.set_ownership_recursively(consts.SSPL_CONFIGURED, sspl_uid, sspl_gid)

        # Get the types of server and storage we are currently running on and
        # enable/disable sensor groups in the conf file accordingly.
        update_sensor_info(consts.SSPL_CONFIG_INDEX, self.node_type,
            self.enclosure_type)

        # Message bus topic creation
        self.create_message_types()

        # Skip this step if sspl is being configured for node replacement
        # scenario as consul data is already
        # available on healthy node
        # Updating build requested log level
        if not os.path.exists(consts.REPLACEMENT_NODE_ENV_VAR_FILE):
            with open(f"{consts.SSPL_BASE_DIR}/low-level/files/opt/seagate" + \
                "/sspl/conf/build-requested-loglevel") as f:
                log_level = f.read().strip()

            if not log_level:
                log_level = "INFO"

            if log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                Conf.set(consts.SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>log_level", log_level)
                Conf.save(consts.SSPL_CONFIG_INDEX)
            else:
                raise SetupError(errno.EINVAL,
                    "Unexpected log level is requested, '%s'", log_level)

    def create_message_types(self):
        # Skip this step if sspl is being configured for node
        # replacement scenario as rabbitmq cluster is
        # already configured on the healthy node
        # Configure rabbitmq
        if not os.path.exists(consts.REPLACEMENT_NODE_ENV_VAR_FILE):
            message_types = [Conf.get(consts.SSPL_CONFIG_INDEX,
                                      "INGRESSPROCESSOR"
                                      ">message_type"),
                             Conf.get(consts.SSPL_CONFIG_INDEX,
                                      "EGRESSPROCESSOR"
                                      ">message_type")]
            mbadmin = MessageBusAdmin(admin_id="admin")
            try:
                mbadmin.register_message_type(message_types=message_types,
                                              partitions=1)
            except MessageBusError as e:
                if self.topic_already_exists not in e.desc:
                    # if topic not already exists, raise exception
                    raise e
