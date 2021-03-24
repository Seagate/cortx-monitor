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
import consul

from cortx.utils.message_bus import MessageBus, MessageBusAdmin
from cortx.utils.message_bus.error import MessageBusError
from framework.base import sspl_constants as consts
from cortx.utils.service import DbusServiceHandler
from cortx.utils.process import SimpleProcess
from cortx.utils.validator.v_service import ServiceV
from .setup_error import SetupError
from cortx.utils.conf_store import Conf
from .conf_based_sensors_enable import update_sensor_info


class SSPLConfig:
    """SSPL Setup Config Interface."""

    name = "config"

    def __init__(self):
        """Init method for sspl setup config."""
        self._script_dir = os.path.dirname(os.path.abspath(__file__))
        # Load sspl and global configs
        Conf.load(consts.SSPL_CONFIG_INDEX, consts.sspl_config_path)
        global_config_url = Conf.get(
            consts.SSPL_CONFIG_INDEX,
            "SYSTEM_INFORMATION>global_config_copy_url")
        Conf.load(consts.GLOBAL_CONFIG_INDEX, global_config_url)
        self.product = Conf.get(consts.GLOBAL_CONFIG_INDEX, 'release>product')
        self.topic_already_exists = "ALREADY_EXISTS"

    def validate(self):
        """Validate config for supported role and product"""
        # Validate role
        self.role = Conf.get(consts.GLOBAL_CONFIG_INDEX, 'release>setup')
        if not self.role:
            raise SetupError(
                errno.EINVAL,
                "%s - validation failure. %s",
                self.name,
                "Role not found in global config copy.")
        if self.role not in consts.setups:
            raise SetupError(
                errno.EINVAL,
                "%s - validation failure. %s",
                self.name,
                "Role '%s' is not supported. Check Usage" % self.role)

    def replace_expr(self, filename: str, key, new_str: str):

        """The function helps to replace the expression provided as key
            with new string in the file provided in filename
            OR
            It inserts the new string at given line as a key in the
            provided file.
        """

        with open(filename, 'r+') as f:
            lines = f.readlines()
            if isinstance(key, str):
                for i, line in enumerate(lines):
                    if re.search(key, line):
                        lines[i] = re.sub(key, new_str, lines[i])
            elif isinstance(key, int):
                if not re.search(new_str, lines[key]):
                    lines.insert(key, new_str)
            else:
                raise SetupError(
                    errno.EINVAL,
                    "Key data type : '%s', should be string or int",
                    type(key))
            f.seek(0)
            for line in lines:
                f.write(line)

    def config_sspl(self):
        if (os.geteuid() != 0):
            raise SetupError(
                errno.EINVAL,
                "Run this command with root privileges!!")

        if not os.path.isfile(consts.file_store_config_path):
            raise SetupError(
                errno.EINVAL,
                "Missing configuration!! Create and rerun.",
                consts.file_store_config_path)

        # Put minion id, consul_host and consul_port in conf file
        # Onward LDR_R2, salt will be abstracted out and it won't
        # exist as a hard dependeny of SSPL
        if consts.PRODUCT_NAME == "LDR_R1":
            from framework.utils.salt_util import SaltInterface
            salt_util = SaltInterface()
            salt_util.update_config_file(consts.file_store_config_path)

        if os.path.isfile(consts.SSPL_CONFIGURED):
            os.remove(consts.SSPL_CONFIGURED)

        # Add sspl-ll user to required groups and sudoers file etc.
        sspl_reinit = [
            f"{consts.SSPL_BASE_DIR}/low-level/framework/sspl_reinit",
            self.product]
        _, error, returncode = SimpleProcess(sspl_reinit).run()
        if returncode:
            raise SetupError(returncode,
                             "%s/low-level/framework/sspl_reinit failed for"
                             "product %s with error : %e",
                             consts.SSPL_BASE_DIR, self.product, error
                             )

        os.makedirs(consts.SSPL_CONFIGURED_DIR, exist_ok=True)
        with open(consts.SSPL_CONFIGURED, 'a'):
            os.utime(consts.SSPL_CONFIGURED)

        # SSPL Log file configuration
        # SSPL_LOG_FILE_PATH = self.getval_from_ssplconf('sspl_log_file_path')
        SSPL_LOG_FILE_PATH = Conf.get(
            consts.SSPL_CONFIG_INDEX, 'SYSTEM_INFORMATION>sspl_log_file_path')
        IEM_LOG_FILE_PATH = Conf.get(
            consts.SSPL_CONFIG_INDEX, 'IEMSENSOR>log_file_path')
        if SSPL_LOG_FILE_PATH:
            self.replace_expr(consts.RSYSLOG_SSPL_CONF,
                              'File.*[=,"]', 'File="%s"' % SSPL_LOG_FILE_PATH)
            self.replace_expr(f"{consts.SSPL_BASE_DIR}/low-level/files/etc/logrotate.d/sspl_logs",
                              0, SSPL_LOG_FILE_PATH)

        # IEM configuration
        # Configure log file path in Rsyslog and logrotate configuration file
        IEM_LOG_FILE_PATH = Conf.get(
            consts.SSPL_CONFIG_INDEX, 'IEMSENSOR>log_file_path')

        if IEM_LOG_FILE_PATH:
            self.replace_expr(consts.RSYSLOG_IEM_CONF,
                              'File.*[=,"]', 'File="%s"' % IEM_LOG_FILE_PATH)
            self.replace_expr(
                f'{consts.SSPL_BASE_DIR}/low-level/files/etc/logrotate.d/iem_messages',
                0, IEM_LOG_FILE_PATH)
        else:
            self.replace_expr(consts.RSYSLOG_IEM_CONF,
                              'File.*[=,"]',
                              'File="/var/log/%s/iem/iem_messages"' %
                              consts.PRODUCT_FAMILY)

        # Create logrotate dir in case it's not present for dev environment
        if not os.path.exists(consts.LOGROTATE_DIR):
            os.makedirs(consts.LOGROTATE_DIR)

        shutil.copy2(
            '%s/low-level/files/etc/logrotate.d/iem_messages' %
            consts.SSPL_BASE_DIR,
            consts.IEM_LOGROTATE_CONF)

        shutil.copy2('%s/low-level/files/etc/logrotate.d/sspl_logs' %
                     consts.SSPL_BASE_DIR, consts.SSPL_LOGROTATE_CONF)

        # This rsyslog restart will happen after successful updation of rsyslog
        # conf file and before sspl starts. If at all this will be removed from
        # here, there will be a chance that SSPL intial logs will not be present in
        # "/var/log/<product>/sspl/sspl.log" file. So, initial logs needs to be collected from
        # "/var/log/messages"
        service = DbusServiceHandler()
        service.restart('rsyslog.service')

        # For node replacement scenario consul will not be running on the new node. But,
        # there will be two instance of consul running on healthy node. When new node is configured
        # consul will be brought back on it. We are using VIP to connect to consul. So, if consul
        # is not running on new node, we dont need to error out.
        # If consul is not running, exit
        # Onward LDR_R2, consul will be abstracted out and it won't
        # exit as hard dependeny of SSPL

        if consts.PRODUCT_NAME == 'LDR_R1':
            if not os.path.exists(consts.REPLACEMENT_NODE_ENV_VAR_FILE):
                ServiceV().validate('isrunning', ['consul'], is_process=True)

        # Get the types of server and storage we are currently running on and
        # enable/disable sensor groups in the conf file accordingly.
        update_sensor_info(consts.SSPL_CONFIG_INDEX)

        self.create_message_types()

    def create_message_types(self):
        # Skip this step if sspl is being configured for node
        # replacement scenario as rabbitmq cluster is
        # already configured on the healthy node
        # Configure rabbitmq
        if not os.path.exists(consts.REPLACEMENT_NODE_ENV_VAR_FILE):
            message_types = [Conf.get(consts.SSPL_CONFIG_INDEX,
                                      "RABBITMQINGRESSPROCESSOR"
                                      ">message_type"),
                             Conf.get(consts.SSPL_CONFIG_INDEX,
                                      "RABBITMQEGRESSPROCESSOR"
                                      ">message_type")]
            mb = MessageBus()
            mbadmin = MessageBusAdmin(mb, admin_id='admin')
            try:
                mbadmin.register_message_type(message_types=message_types,
                                              partitions=1)
            except MessageBusError as e:
                if self.topic_already_exists in e.desc:
                    # Topic already exists
                    pass
                else:
                    raise e

    def process(self):
        cmd = "config"
        if (cmd == "config"):
            self.config_sspl()
        else:
            raise SetupError(errno.EINVAL, "cmd val should be config")

        # Skip this step if sspl is being configured for node replacement
        # scenario as consul data is already
        # available on healthy node
        # Updating build requested log level
        if not os.path.exists(consts.REPLACEMENT_NODE_ENV_VAR_FILE):
            with open(f'{consts.SSPL_BASE_DIR}/low-level/files/opt/seagate'
                      '/sspl/conf/build-requested-loglevel', 'r') as f:
                log_level = f.readline().strip()

            if not log_level:
                log_level = "INFO"

            if log_level == "DEBUG" or log_level == "INFO" or \
                    log_level == "WARNING" or log_level == "ERROR" or \
                    log_level == "CRITICAL":
                if consts.PRODUCT_NAME == "LDR_R1":
                    host = os.getenv('CONSUL_HOST', consts.CONSUL_HOST)
                    port = os.getenv('CONSUL_PORT', consts.CONSUL_PORT)
                    consul_conn = consul.Consul(host=host, port=port)
                    consul_conn.kv.put(
                        "sspl/config/SYSTEM_INFORMATION/log_level",
                        log_level)
                else:
                    Conf.set(consts.SSPL_CONFIG_INDEX,
                             'SYSTEM_INFORMATION>log_level', log_level)
                    Conf.save(consts.SSPL_CONFIG_INDEX)
            else:
                raise SetupError(
                    errno.EINVAL,
                    "Unexpected log level is requested, '%s'",
                    log_level
                )
