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
import json
import re
import errno
import consul

from cortx.sspl.bin import sspl_constants as consts
from cortx.utils.service import Service
from cortx.utils.process import SimpleProcess
from cortx.utils.validator.v_service import ServiceV
from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.error import SetupError
from cortx.utils.conf_store import Conf
from cortx.sspl.bin.conf_based_sensors_enable import update_sensor_info


class SSPLConfig:

    """SSPL Setup Config Interface."""

    name = "config"

    def __init__(self):
        """Init method for sspl setup config."""
        self._script_dir = os.path.dirname(os.path.abspath(__file__))
        # Load sspl and global configs
        Conf.load(consts.SSPL_CONFIG_INDEX, consts.sspl_config_path)
        global_config_url = Conf.get(
            consts.SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_dump_url")
        Conf.load(consts.GLOBAL_CONFIG_INDEX, global_config_url)

    def validate(self):
        """Validate config for supported role and product"""
        # Validate role
        self.role = Conf.get(consts.GLOBAL_CONFIG_INDEX, 'release>setup')
        if not self.role:
            raise SetupError(
                errno.EINVAL,
                "%s - validation failure. %s",
                self.name,
                "Role not found in SSPL global config dump.")
        if self.role not in consts.setups:
            raise SetupError(
                errno.EINVAL,
                "%s - validation failure. %s",
                self.name,
                "Role '%s' is not supported. Check Usage" % self.role)

        # Validate Product
        self.product = Conf.get(consts.GLOBAL_CONFIG_INDEX, 'release>product')
        if not consts.enabled_products:
            raise SetupError(errno.EINVAL, "No enabled products!")
        if self.product not in consts.enabled_products:
            raise SetupError(
                errno.EINVAL,
                "Product '%s' is not in enabled products list: %s",
                self.product, consts.enabled_products)

    def replace_expr(self, filename:str, key, new_str:str):

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
        if(os.geteuid() != 0):
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
            from cortx.sspl.bin.salt_util import SaltInterface
            salt_util = SaltInterface()
            salt_util.update_config_file(consts.file_store_config_path)

        if os.path.isfile(consts.SSPL_CONFIGURED):
            os.remove(consts.SSPL_CONFIGURED)

        # Add sspl-ll user to required groups and sudoers file etc.
        sspl_reinit = [f"{consts.SSPL_BASE_DIR}/bin/sspl_reinit", self.product]
        _ , error, returncode = SimpleProcess(sspl_reinit).run()
        if returncode:
            raise SetupError(returncode,
                    "%s/bin/sspl_reinit failed for product %s with error : %e",
                      consts.SSPL_BASE_DIR, product, error
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
            self.replace_expr(
                    f"{consts.SSPL_BASE_DIR}/low-level/files/etc/logrotate.d/sspl_logs",
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
                    'File.*[=,"]', 'File="/var/log/%s/iem/iem_messages"' % consts.PRODUCT_FAMILY)

        # Create logrotate dir in case it's not present for dev environment
        if not os.path.exists(consts.LOGROTATE_DIR):
            os.makedirs(consts.LOGROTATE_DIR)

        shutil.copy2(
            '%s/low-level/files/etc/logrotate.d/iem_messages' % consts.SSPL_BASE_DIR,
            consts.IEM_LOGROTATE_CONF)

        shutil.copy2(
            '%s/low-level/files/etc/logrotate.d/sspl_logs' % consts.SSPL_BASE_DIR,
            consts.SSPL_LOGROTATE_CONF)

        # This rsyslog restart will happen after successful updation of rsyslog
        # conf file and before sspl starts. If at all this will be removed from
        # here, there will be a chance that SSPL intial logs will not be present in
        # "/var/log/<product>/sspl/sspl.log" file. So, initial logs needs to be collected from
        # "/var/log/messages"

        Service('dbus').process("restart", 'rsyslog.service')

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

    def get_rabbitmq_cluster_nodes(self):
        cluster_nodes = None
        if  self.rabbitmq_major_release == '3' and \
            self.rabbitmq_maintenance_release == '8':

            rmq_cluster_status_cmd = '/usr/sbin/rabbitmqctl cluster_status' + \
                                    ' --formatter json'
            output, error, returncode = SimpleProcess(rmq_cluster_status_cmd).run()
            try:
                rabbitmq_cluster_status = json.loads(output)
            except Exception:
                raise SetupError(
                            errno.EINVAL,
                            "RabbitMQ cluster status is not okay! \n, status : %s",
                            output)
            if returncode:
                raise SetupError(returncode, error)
            running_nodes = rabbitmq_cluster_status['running_nodes']
            for i, node in enumerate(running_nodes):
                running_nodes[i] = node.replace('rabbit@', '')
            cluster_nodes = " ".join(running_nodes)
        elif self.rabbitmq_version == '3.3.5':
            rmq_cluster_status_cmd = "rabbitmqctl cluster_status"
            output, error, returncode = SimpleProcess(rmq_cluster_status_cmd).run()
            cluster_nodes = re.search(
                        r"running_nodes,\['rabbit@(?P<cluster_nodes>.+?)'\]",
                        output.decode()).groupdict()["cluster_nodes"]
        else:
            raise SetupError(
                        errno.EINVAL,
                        "This RabbitMQ version : %s is not supported",
                        self.rabbitmq_version)
        return cluster_nodes

    def get_cluster_running_nodes(self, msg_broker : str):
        if(msg_broker == 'rabbitmq'):
            return self.get_rabbitmq_cluster_nodes()
        else:
            raise SetupError(errno.EINVAL,
                        "Provided message broker '%s' is not supported",
                        msg_broker)

    def process(self):
        cmd = "config"
        if(cmd == "config"):
            self.config_sspl()
        else:
            raise SetupError(errno.EINVAL, "cmd val should be config")

        # Get the version. Output can be 3.3.5 or 3.8.9 or in this format
        rmq_cmd = "rpm -qi rabbitmq-server"
        output, error, returncode = SimpleProcess(rmq_cmd).run()
        if returncode:
            raise SetupError(returncode, error)
        self.rabbitmq_version = re.search(  r'Version     :\s*([\d.]+)',
                                            str(output)).group(1)

        # Get the Major release version parsed. (Eg: 3 from 3.8.9)
        self.rabbitmq_major_release = self.rabbitmq_version[0]

        # Get the Minor release version parsed. (Eg: 3.8 from 3.8.9)
        self.rabbitmq_minor_release = self.rabbitmq_version[:3]

        # Get the Maitenance release version parsed from minor release.
        # (Eg: 8 from 3.8)
        self.rabbitmq_maintenance_release = self.rabbitmq_minor_release[-1]

        # Skip this step if sspl is being configured for node replacement
        # scenario as consul data is already
        # available on healthy node
        # Updating RabbitMQ cluster nodes.
        # In node replacement scenario, avoiding feeding again to avoid
        # over writing already configured values
        # with which rabbitmq cluster may have been created
        if not os.path.exists(consts.REPLACEMENT_NODE_ENV_VAR_FILE):
            message_broker="rabbitmq"
            # Get the running nodes from a cluster
            pout = self.get_cluster_running_nodes(message_broker)

            # Update cluster_nodes key in consul
            if consts.PRODUCT_NAME == 'LDR_R1':
                host = os.getenv('CONSUL_HOST', consts.CONSUL_HOST)
                port = os.getenv('CONSUL_PORT', consts.CONSUL_PORT)
                consul_conn = consul.Consul(host=host, port=port)
                consul_conn.kv.put(
                        "sspl/config/RABBITMQCLUSTER/cluster_nodes", pout)
            else:
                Conf.set(consts.SSPL_CONFIG_INDEX,
                         'RABBITMQCLUSTER>cluster_nodes', pout)
                Conf.save(consts.SSPL_CONFIG_INDEX)

        # Skip this step if sspl is being configured for node replacement
        # scenario as consul data is already
        # available on healthy node
        # Updating build requested log level
        if not os.path.exists(consts.REPLACEMENT_NODE_ENV_VAR_FILE):
            with open(f'{consts.SSPL_BASE_DIR}/low-level/files/opt/seagate' + \
                '/sspl/conf/build-requested-loglevel', 'r') as f:
                log_level = f.readline().strip()

            if not log_level:
                log_level = "INFO"

            if  log_level == "DEBUG" or log_level == "INFO" or \
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
