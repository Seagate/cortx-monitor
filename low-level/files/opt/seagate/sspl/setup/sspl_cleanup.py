#!/bin/env python3

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import shutil
import os
import pwd

from cortx.utils.conf_store import Conf
from cortx.utils.process import SimpleProcess
from cortx.utils.message_bus import MessageBus, MessageBusAdmin
from cortx.utils.message_bus.error import MessageBusError
from framework.utils.filestore import FileStore
from files.opt.seagate.sspl.setup.setup_logger import logger
from framework.utils.utility import Utility
from framework.base.sspl_constants import (
    SSPL_CONFIG_INDEX, file_store_config_path, global_config_file_path,
    sspl_config_path, PRODUCT_BASE_DIR, SSPL_BASE_DIR, PRODUCT_FAMILY,
    USER)


class SSPLCleanup:
    """Reset config and optionally factory operation."""

    def __init__(self, args):
        """Initialize cleanup instance."""
        self.pre_factory = False
        if "--pre-factory" in args:
            self.pre_factory = True

    def validate(self):
        """Validate inputs required for cleanup."""
        pass

    def process(self, product):
        """Reset and cleanup config.

        if self.pre_factory:
            Cleanup sspl log and config files and rollback all steps executed
            in post_install stage.
        else:
            Reset sspl config.
        """
        try:
            if os.path.exists(file_store_config_path):
                FileStore().delete(
                    file_store_config_path)
            shutil.copyfile("%s/conf/sspl.conf.%s.yaml" % (
                SSPL_BASE_DIR, product), file_store_config_path)
            if self.pre_factory:
                self.cleanup_log_and_config()
        except OSError as e:
            logger.error(f"Failed in Cleanup. ERROR: {e}")

    @staticmethod
    def cleanup_log_and_config():
        """--pre-factory cleanup : Cleanup logs, config files and
        undo everything whatever was done in post-install Mini-Provisioner
        Interface."""
        Conf.load(SSPL_CONFIG_INDEX, sspl_config_path)
        sspl_log_file_path = Utility.get_config_value(
            SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>sspl_log_file_path")
        iem_log_file_path = Utility.get_config_value(
            SSPL_CONFIG_INDEX, "IEMSENSOR>log_file_path")
        message_types = [
            Utility.get_config_value(SSPL_CONFIG_INDEX, "INGRESSPROCESSOR>message_type"),
            Utility.get_config_value(SSPL_CONFIG_INDEX, "EGRESSPROCESSOR>message_type")]

        # Directories and file which needs to deleted.
        directories = [
            f'/var/{PRODUCT_FAMILY}/sspl', f'/var/{PRODUCT_FAMILY}/iem/',
            f'/var/log/{PRODUCT_FAMILY}/sspl/', f'/var/log/{PRODUCT_FAMILY}/iem/',
            '/etc/sspl-ll/', f'{PRODUCT_BASE_DIR}/iem/iec_mapping']

        sspl_sudoers_file = '/etc/sudoers.d/sspl'
        sspl_dbus_policy_rules = '/etc/polkit-1/rules.d/sspl-ll_dbus_policy.rules'
        sspl_dbus_policy_conf = '/etc/dbus-1/system.d/sspl-ll_dbus_policy.conf'
        sspl_service_file = '/etc/systemd/system/sspl-ll.service'
        sspl_test_backup = '/etc/sspl_tests.conf.back'
        sspl_test_file_path = '/etc/sspl_test_gc_url.yaml'
        sspl_sb_log_file_path = sspl_log_file_path.replace(
            "/sspl.log", "/sspl_support_bundle.log")
        manifest_log_file_path = sspl_log_file_path.replace(
            "/sspl.log", "/manifest.log")

        # symlinks created during post_install
        sspl_ll_cli = "/usr/bin/sspl_ll_cli"

        # Remove SSPL config other config/log files which were
        # created during post_install.
        for filepath in [
            sspl_ll_cli, sspl_test_backup, sspl_test_file_path,
            file_store_config_path, global_config_file_path, sspl_log_file_path,
            iem_log_file_path, sspl_sb_log_file_path, manifest_log_file_path,
            sspl_dbus_policy_conf, sspl_dbus_policy_rules,
            sspl_sudoers_file, sspl_service_file]:
            FileStore().delete(filepath)

        # Delete directories which were created during post_install.
        for directory in directories:
            FileStore().delete(directory)
        logger.info("Deleted config/log files and directories.")

        # Delete sspl-ll user
        usernames = [x[0] for x in pwd.getpwall()]
        if USER in usernames:
            _, err, rc = SimpleProcess("/usr/sbin/userdel -f %s" % USER).run()
            if rc != 0:
                logger.info("Error occurref while deleteing %s user. ERROR: %s"
                    %(USER, err))
            else:
                logger.info("Deleted %s user." % USER)

        # Delete topic
        mbadmin = MessageBusAdmin(admin_id="admin")
        try:
            mbadmin.deregister_message_type(message_types)
            logger.info("Delete kafka %s topics." % message_types)
        except MessageBusError as e:
            logger.error(f"MessageBusError occurred while deleting topic:{e}")
