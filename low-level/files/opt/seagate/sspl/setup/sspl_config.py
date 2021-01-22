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
import psutil
import json
import re
import errno

from cortx.sspl.bin import sspl_constants as consts
from cortx.sspl.bin.salt_util import SaltInterface
from cortx.utils.service import Service
from cortx.utils.process import SimpleProcess

class SSPLConfigError(Exception):
    """ Generic Exception with error code and output """

    def __init__(self, rc, message, *args):
        """SSPLConfigError init."""
        self._rc = rc
        self._desc = message % (args)

    def __str__(self):
        """SSPLConfigError str."""
        if self._rc == 0: return self._desc
        return "error(%d): %s" %(self._rc, self._desc)

class SSPLConfig:
    """ SSPL Setup Config Interface """

    name = "config"
    DIR_NAME= f"/opt/seagate/{consts.PRODUCT_FAMILY}/sspl"
    RSYSLOG_CONF ="/etc/rsyslog.d/0-iemfwd.conf"
    RSYSLOG_SSPL_CONF = "/etc/rsyslog.d/1-ssplfwd.conf"
    LOGROTATE_DIR  ="/etc/logrotate.d"
    IEM_LOGROTATE_CONF = f"{LOGROTATE_DIR}/iem_messages"
    SSPL_LOGROTATE_CONF = f"{LOGROTATE_DIR}/sspl_logs"
    SSPL_CONFIGURED_DIR = f"/var/{consts.PRODUCT_FAMILY}/sspl"
    SSPL_CONFIGURED = f"{SSPL_CONFIGURED_DIR}/sspl-configured"


    def __init__(self, args : list):
        self.args = args
        self._script_dir = os.path.dirname(os.path.abspath(__file__))
        self.force = 0
        self.role = None
        self.rmq_cluster_nodes = None
        self.read_provisioner_config = True

    def getval_from_ssplconf(self, varname : str) -> str:
        with open(consts.file_store_config_path, mode='rt') as confile:
            for line in confile:
                if line.startswith(varname):
                    rets = line.split('=')[1]
                    if(rets.endswith('\n')):
                        rets = rets.replace('\n', '')
                    return rets
        return None

    def replace_expr(self, filename:str, key, new_str:str):
        with open(filename, 'r+') as f: 
            lines = f.readlines()
            if type(key) == str:
                for i, line in enumerate(lines):                 
                    if re.search(key, line):
                        lines[i] = re.sub(key, new_str, lines[i])
            elif type(key) == int:
                if not re.search(new_str, lines[key]):
                    lines.insert(key, new_str)
            else 
                raise SSPLConfigError(
                            errno.EINVAL,
                            "Key data type : '%s', should be string or int",
                            type(key))
            f.seek(0)
            for line in lines:
                f.write(line)

    def validate_args(self):
        i = 0
        while i < len(self.args):
            if self.args[i] == '-f':
                self.force = 1
            elif self.args[i] == '-r':
                i+=1
                if i >= len(self.args):
                    raise SSPLConfigError(errno.EINVAL, 
                                "self.Role is not provided with -r option") 
                if self.args[i] not in consts.self.roles:
                    raise SSPLConfigError(errno.EINVAL, 
                                "Provided self.role '%s' is not supported", 
                                self.args[i])
                else:
                    self.role = self.args[i]
            elif self.args[i] == '-n':
                i+=1
                if i >= len(self.args):
                    raise SSPLConfigError(errno.EINVAL, 
                                "Node is not provided with -n option") 
                else:
                    self.rmq_cluster_nodes = self.args[i]
            elif self.args[i] == '-d':
                self.read_provisioner_config = False
            else:
                raise SSPLConfigError(errno.EINVAL, 
                                "Unknown option '%s'", self.args[i])
            i+=1

    def config_sspl(self):
        self.validate_args()
        if(os.geteuid() != 0):
            raise SSPLConfigError(
                        errno.EINVAL, 
                        "Run this command with root privileges!!")
        
        if not os.path.isfile(consts.file_store_config_path):
            raise SSPLConfigError(
                        errno.EINVAL, 
                        "Missing configuration!! Create and rerun.",
                        consts.file_store_config_path)

        # Put minion id, consul_host and consul_port in conf file
        # Onward LDR_R2, salt will be abstracted out and it won't
        # exist as a hard dependeny of SSPL
        if consts.PRODUCT_NAME == "LDR_R1":
            salt_util = SaltInterface()
            salt_util.update_config_file(consts.file_store_config_path)

        if os.path.isfile(self.SSPL_CONFIGURED):
            ans = 'y' if self.force == 1 else None

            while ans!='y' and ans!='n':
                ans = input("SSPL is already initialized. \
                            Reinitialize SSPL? [y/n]: ")
            
            if(ans == 'n'):
                raise SSPLConfigError(
                        errno.EINVAL, 
                        "SSPL already initialized, reinitialization cancled.")

            try:
                os.remove(self.SSPL_CONFIGURED)
            except OSError:
                raise

        # Get Product
        product = self.getval_from_ssplconf('product')
        
        if not product:
            raise SSPLConfigError(
                        errno.EINVAL, 
                        "No product specified in %s",
                        consts.file_store_config_path)
        
        if not consts.enabled_products:
            raise SSPLConfigError(errno.EINVAL, "No enabled products!")
        
        if product not in consts.enabled_products:
            raise SSPLConfigError(
                        errno.EINVAL, 
                        "Product '%s' is not in enabled products list: %s",
                        product, consts.enabled_products)

        # Configure self.role
        if self.role:
            self.replace_expr(consts.file_store_config_path, 
                            '^setup=.*', f'setup={self.role}')

        # Add sspl-ll user to required groups and sudoers file etc.
        print("Initializing SSPL configuration ... ")
        sspl_reinit = [f"{self.DIR_NAME}/bin/sspl_reinit", product]
        output, error, returncode = SimpleProcess(sspl_reinit).run()
        if returncode:
            raise SSPLConfigError(returncode, 
                    "%s/bin/sspl_reinit failed for product %s",
                      self.DIR_NAME, product
                    )

        print("SSPL configured successfully.")

        os.makedirs(self.SSPL_CONFIGURED_DIR, exist_ok=True)
        with open(self.SSPL_CONFIGURED, 'a'):
            os.utime(self.SSPL_CONFIGURED)
        print(f'touched file : {self.SSPL_CONFIGURED}')

        # SSPL Log file configuration
        SSPL_LOG_FILE_PATH = self.getval_from_ssplconf('sspl_log_file_path')
        if SSPL_LOG_FILE_PATH:
            self.replace_expr(self.RSYSLOG_SSPL_CONF, 
                        'File.*[=,"]', f'File="{SSPL_LOG_FILE_PATH}"')
            self.replace_expr(
                    f"{self.DIR_NAME}/low-level/files/etc/logrotate.d/sspl_logs", 
                    0, SSPL_LOG_FILE_PATH)

        # IEM configuration
        # Configure log file path in Rsyslog and logrotate configuration file
        LOG_FILE_PATH = self.getval_from_ssplconf('log_file_path')

        if LOG_FILE_PATH:
            self.replace_expr(self.RSYSLOG_CONF, 
                    'File.*[=,"]', f'File="{LOG_FILE_PATH}"')
            self.replace_expr(
                    f'{self.DIR_NAME}/low-level/files/etc/logrotate.d/iem_messages', 
                    0, LOG_FILE_PATH)
        else:
            self.replace_expr(self.RSYSLOG_CONF, 
                    'File.*[=,"]', f'File=/var/log/{consts.PRODUCT_FAMILY}/iem/iem_messages')


        # Create logrotate dir in case it's not present for dev environment
        if not os.path.exists(self.LOGROTATE_DIR):
            os.makedirs(self.LOGROTATE_DIR)

        shutil.copy2(f'{self.DIR_NAME}/low-level/files/etc/logrotate.d/iem_messages', self.IEM_LOGROTATE_CONF)
        shutil.copy2(f'{self.DIR_NAME}/low-level/files/etc/logrotate.d/sspl_logs', self.SSPL_LOGROTATE_CONF)
        
        # This rsyslog restart will happen after successful updation of rsyslog
        # conf file and before sspl starts. If at all this will be removed from
        # here, there will be a chance that SSPL intial logs will not be present in
        # "/var/log/<product>/sspl/sspl.log" file. So, initial logs needs to be collected from
        # "/var/log/messages"
        try :
            Service('dbus').process("restart", 'rsyslog.service')
        except Exception:
            raise

        # For node replacement scenario consul will not be running on the new node. But,
        # there will be two instance of consul running on healthy node. When new node is configured
        # consul will be brought back on it. We are using VIP to connect to consul. So, if consul
        # is not running on new node, we dont need to error out.
        # If consul is not running, exit
        # Onward LDR_R2, consul will be abstracted out and it won't
        # exit as hard dependeny of SSPL

        if consts.PRODUCT_NAME == 'LDR_R1':
            if not os.path.exists(consts.REPLACEMENT_NODE_ENV_VAR_FILE):
                CONSUL_PS = None
                for proc in psutil.process_iter():
                    if 'consul' in proc.name():
                        CONSUL_PS = proc.pid
                if not CONSUL_PS:
                    raise SSPLConfigError(
                            errno.EINVAL,
                            "Consul is not running, exiting..")

        # Get the types of server and storage we are currently running on and
        # enable/disable sensor groups in the conf file accordingly.
        if self.read_provisioner_config:
            from cortx.sspl.bin.conf_based_sensors_enable import update_sensor_info
            update_sensor_info()    
            
    def get_rabbitmq_cluster_nodes(self):
        pout = None
        if  self.rabbitmq_major_release == '3' and \
            self.rabbitmq_maintenance_release == '8':

            rmq_cluster_status_cmd = '/usr/sbin/rabbitmqctl cluster_status \
                                    --formatter json'
            output, error, returncode = SimpleProcess(rmq_cluster_status_cmd).run()
            rabbitmq_cluster_status = json.loads(output)
            if returncode:
                raise SSPLConfigError(returncode, error)
            running_nodes = rabbitmq_cluster_status['running_nodes']
            for i, node in enumerate(running_nodes):
                running_nodes[i] = node.replace('rabbit@', '')
            pout = " ".join(running_nodes)
        elif self.rabbitmq_version == '3.3.5':
            rmq_cluster_status_cmd = "rabbitmqctl cluster_status | grep running_nodes | cut -d '[' -f2 | cut -d ']' -f1 | sed 's/rabbit@//g' | sed 's/,/, /g'"
            output, error, returncode = SimpleProcess(rmq_cluster_status_cmd).run()
            pout = output.replace("'", '').replace(' ', '')
        else:
            raise SSPLConfigError(errno.EINVAL, "This RabbitMQ version : %s is not supported", self.rabbitmq_version)

        return pout

    def get_cluster_running_nodes(self, msg_broker : str):
        if(msg_broker == 'rabbitmq'):
            return self.get_rabbitmq_cluster_nodes()
        else:
            raise SSPLConfigError(errno.EINVAL, 
                        "Provided message broker '%s' is not supported", 
                        msg_broker
                        )       
            

    def process(self):
        cmd = "config"
        if(cmd == "config"):
            self.config_sspl()
        else:
            raise SSPLConfigError(errno.EINVAL, "cmd val should be config")

        # Get the version. Output can be 3.3.5 or 3.8.9 or in this format
        rmq_cmd = "rpm -qi rabbitmq-server"
        output, error, returncode = SimpleProcess(rmq_cmd).run()
        if returncode:
            raise SSPLConfigError(returncode, error)
        self.rabbitmq_version = re.search(r'Version     :\s*([\d.]+)', str(output)).group(1)

        # Get the Major release version parsed. (Eg: 3 from 3.8.9)
        self.rabbitmq_major_release = self.rabbitmq_version[0]

        # Get the Minor release version parsed. (Eg: 3.8 from 3.8.9)
        self.rabbitmq_minor_release = self.rabbitmq_version[:3] 

        # Get the Maitenance release version parsed from minor release. (Eg: 8 from 3.8)
        self.rabbitmq_maintenance_release = self.rabbitmq_minor_release[-1]

        # Skip this step if sspl is being configured for node replacement scenario as consul data is already
        # available on healthy node
        # Updating RabbitMQ cluster nodes.
        # In node replacement scenario, avoiding feeding again to avoid over writing already configured values
        # with which rabbitmq cluster may have been created
        if not consts.REPLACEMENT_NODE_ENV_VAR_FILE:
            message_broker="rabbitmq"
            # Get the running nodes from a cluster
            pout = self.get_cluster_running_nodes(message_broker)

            # Update cluster_nodes key in consul
            if consts.PRODUCT_NAME == 'LDR_R1':
                consul_cmd = f'{consts.CONSUL_PATH}/consul kv put sspl/config/RABBITMQCLUSTER/cluster_nodes {pout}'
                output, error, returncode = SimpleProcess(consul_cmd).run()
                if returncode:
                    raise SSPLConfigError(returncode, error, consul_cmd)
                if self.rmq_cluster_nodes:
                    consul_cmd = f'{consts.CONSUL_PATH}/consul kv put sspl\
                        /config/RABBITMQCLUSTER/cluster_nodes {self.rmq_cluster_nodes}'
                    output, error, returncode = SimpleProcess(consul_cmd).run()
                    if returncode:
                        raise SSPLConfigError(returncode, error, consul_cmd)
                else:
                    self.replace_expr(consts.file_store_config_path, 'cluster_nodes=.*', f'cluster_nodes={pout}')
            
        # Skip this step if sspl is being configured for node replacement scenario as consul data is already
        # available on healthy node
        # Updating build requested log level
        if not consts.REPLACEMENT_NODE_ENV_VAR_FILE:
            log_level = None
            with open(f'{self.DIR_NAME}/low-level/files/opt/seagate/sspl/conf/build-requested-loglevel', 'r') as f:
                log_level = f.readline()
            
            if( log_level == "DEBUG" or log_level == "INFO" or \
                log_level == "WARNING" or log_level == "ERROR" or \
                log_level == "CRITICAL"                     
                ):
                if consts.PRODUCT_NAME == "LDR_R1":
                    consul_cmd = f'{consts.CONSUL_PATH}/consul kv put sspl/config/SYSTEM_INFORMATION/log_level {log_level}'
                    output, error, returncode = SimpleProcess(consul_cmd).run()
                    if returncode:
                        raise SSPLConfigError(returncode, error, consul_cmd)
                else:
                    self.replace_expr(consts.file_store_config_path, 'log_level.*[=,",\']', f'log_level={log_level}')
            else:
                raise SSPLConfigError(
                            errno.EINVAL,
                            "Unexpected log level is requested, '%s'",
                            log_level
                            )      
