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
# - Configures role in sspl.conf if supplied
# - Executes sspl_reinit script
# - Updates cluster nodes passed in cli to consul
#################################################################

import os
import sys
import subprocess
import shutil
import psutil
import json
sys.path.insert(0, '/opt/seagate/cortx/sspl/low-level/')

import rpm
import dbus

from framework.base import sspl_constants as consts
from framework.utils.salt_util import SaltInterface

class Config:
    """ Config Interface """

    name = "config"
    DIR_NAME= f"/opt/seagate/{consts.PRODUCT_FAMILY}/sspl"
    RSYSLOG_CONF ="/etc/rsyslog.d/0-iemfwd.conf"
    RSYSLOG_SSPL_CONF = "/etc/rsyslog.d/1-ssplfwd.conf"
    LOGROTATE_DIR  ="/etc/logrotate.d"
    IEM_LOGROTATE_CONF = f"{LOGROTATE_DIR}/iem_messages"
    SSPL_LOGROTATE_CONF = f"{LOGROTATE_DIR}/sspl_logs"
    SSPL_CONFIGURED = f"/var/{consts.PRODUCT_FAMILY}/sspl/sspl-configured"
    SSPL_CONFIGURED_DIR = f"/var/{consts.PRODUCT_FAMILY}/sspl"


    def __init__(self, args : list):
        self.args = args
        self._script_dir = os.path.dirname(os.path.abspath(__file__))
        # to get rpm info
        self.ts = rpm.TransactionSet()
        # to interact with systemd
        self.sysbus = dbus.SystemBus()
        self.systemd1 = sysbus.get_object('org.freedesktop.systemd1', '/org/freedesktop/systemd1')
        self.manager = dbus.Interface(systemd1, 'org.freedesktop.systemd1.Manager')

    def usage(self): 
        sys.stderr.write(
            f"{self.name} [config [-f] [-r <ssu|gw|cmu|vm|cortx>] [-n <node1, node2 name>]]\n"
            "  config options:\n"
            "\t -f  Force reinitialization. Do not prompt\n"
            "\t -r  Role to be configured on the current node\n"
            "\t -n  Nodes which needs to be added into rabbitmq cluster\n"
            "\t -d  Disable reading of config from the provisioner\n"
        )
        sys.exit(1)

    def _send_command(self, command : str, fail_on_error=True):
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()
        if error is not None and len(error) > 0:
            print("command '%s' failed with error\n%s" % (command, error))
            if fail_on_error:
                sys.exit(1)
            else:
                return str(error)

        if type(response) == bytes:
            response = bytes.decode(response)
        return str(response)

    def getval_from_ssplconf(self, varname : str) -> str:
        with open(consts.file_store_config_path, mode='rt') as confile:
            for line in confile:
                if line.find(varname) != -1:
                    return line.split('=')[1]
        return None

    def append_val(self, filename:str, new_str:str , key):
        with open(filename, 'r+') as f: 
            lines = f.readlines()
            if type(key) == str:
                for i, line in enumerate(lines):
                    if line.find(key) != -1:
                        lines[i] = new_str + '\n'
            elif type(key) == int:
                lines.insert(key, new_str)
            f.seek(0)
            for line in lines:
                f.write(line)

    def config_sspl(self):
        force = 0
        role = None
        self.rmq_cluster_nodes = None
        read_provisioner_config = True

        i = 0
        while i < len(self.args):
            if self.args[i] == '-f':
                force = 1
            elif self.args[i] == '-r':
                i+=1
                if i >= len(self.args) or self.args[i] not in consts.roles:
                    self.usage()
                else:
                    role = self.args[i]
            elif self.args[i] == '-n':
                i+=1
                if i >= len(self.args):
                    self.usage()
                else:
                    self.rmq_cluster_nodes = self.args[i]
            elif self.args[i] == '-d':
                read_provisioner_config = False
            else:
                self.usage()
            i+=1

        if(os.geteuid != 0):
            sys.stderr.write("Run this command with root privileges!!")
            sys.exit(1)
        
        if os.path.isfile(consts.file_store_config_path):
            sys.stderr.write(f"Missing configuration!! Create {consts.file_store_config_path} and rerun.")
            sys.exit(1)

        # Put minion id, consul_host and consul_port in conf file
        # Onward LDR_R2, salt will be abstracted out and it won't
        # exist as a hard dependeny of SSPL
        if consts.PRODUCT_NAME == "LDR_R1":
            salt_util = SaltInterface()
            salt_util.update_config_file(consts.file_store_config_path)

        if os.path.isfile(self.SSPL_CONFIGURED):
            ans = 'y' if force == 1 else None

            while ans!='y' or ans!='n':
                ans = input("SSPL is already initialized. Reinitialize SSPL? [y/n]: ")
            
            if(ans!='y'):
                sys.exit(1)

            try:
                os.remove(self.SSPL_CONFIGURED)
            except OSError as error:
                sys.stderr.write(error)
                sys.exit(1)

        # Get Product
        product = self.getval_from_ssplconf('product')
        
        if not product:
            sys.stderr.write(f"No product specified in {consts.file_store_config_path}")
            sys.exit(1)
        
        if not consts.enabled_products:
            sys.stderr.write("No enabled products!")
            sys.exit(1)
        
        if product not in consts.enabled_products:
            sys.stderr.write(f"Product '{product}' is not in enabled products list: {consts.enabled_products}")
            sys.exit(1)

        # Configure role
        if role:
            self.append_val(consts.file_store_config_path, f'setup={role}', 'setup')

        # Add sspl-ll user to required groups and sudoers file etc.
        print("Initializing SSPL configuration ... ")
        reinit_out = subprocess.run([f"{self.DIR_NAME}/bin/sspl_reinit", product], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if reinit_out.returncode:
            sys.stderr.write(
                    f"{self.DIR_NAME}/bin/sspl_reinit failed"
                    f"with exit code {reinit_out.returncode} for product {product}"
                    )
            sys.exit(1)

        print("SSPL configured successfully.")
        os.makedirs(self.SSPL_CONFIGURED_DIR)
        with open(self.SSPL_CONFIGURED, 'a'):
            os.utime(self.SSPL_CONFIGURED)

        # SSPL Log file configuration
        SSPL_LOG_FILE_PATH = self.getval_from_ssplconf('sspl_log_file_path')
        if SSPL_LOG_FILE_PATH:
            self.append_val(self.RSYSLOG_SSPL_CONF, f'action(type="omfile" File="{SSPL_LOG_FILE_PATH}")', 'File')
            ## understand below line and convert
            # sed -i "1 s|^.*$|${SSPL_LOG_FILE_PATH}|g" $DIR_NAME/low-level/files/etc/logrotate.d/sspl_logs
            self.append_val(f"{self.DIR_NAME}/low-level/files/etc/logrotate.d/sspl_logs", SSPL_LOG_FILE_PATH, 0)

        # IEM configuration
        # Configure log file path in Rsyslog and logrotate configuration file
        LOG_FILE_PATH = self.getval_from_ssplconf('log_file_path')

        if LOG_FILE_PATH:
            # sed -i "s|File=.*|File=\"${LOG_FILE_PATH}\"|g" $RSYSLOG_CONF
            self.append_val(self.RSYSLOG_CONF, f'File="{LOG_FILE_PATH}"', 'File=')
            # sed -i "1 s|^.*$|${LOG_FILE_PATH}|g" $DIR_NAME/low-level/files/etc/logrotate.d/iem_messages
            self.append_val(f'{self.DIR_NAME}/low-level/files/etc/logrotate.d/iem_messages', LOG_FILE_PATH, 0)
        else:
            # sed -i "s|File=.*|File=\/var/log/$consts.PRODUCT_FAMILY/iem/iem_messages\"|g" $RSYSLOG_CONF
            self.append_val(self.RSYSLOG_CONF, f'File=/var/log/{consts.PRODUCT_FAMILY}/iem/iem_messages', 'File=')

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

        # subprocess.call(['systemctl', 'restart rsyslog'], shell=False)
        job = self.manager.RestartUnit('rsyslog')

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
                    sys.stderr.write("Consul is not running, exiting..")
                    sys.exit(1)

        # Get the types of server and storage we are currently running on and
        # enable/disable sensor groups in the conf file accordingly.
        if read_provisioner_config:
            subprocess.call(['python3', f'{self._script_dir}/conf_based_sensors_enable'])       
            
    def get_rabbitmq_cluster_nodes(self):
        pout = None
        if self.rabbitmq_major_release == '3' and self.rabbitmq_maintenance_release == '8':
            rabbitmq_cluster_status = self._send_command('/usr/sbin/rabbitmqctl cluster_status --formatter json')
            rabbitmq_cluster_status = json.loads(rabbitmq_cluster_status)
            pout = " ".join(rabbitmq_cluster_status['running_nodes'])
        elif self.rabbitmq_version == '3.3.5':
            out = self._send_command("rabbitmqctl cluster_status | grep running_nodes | cut -d '[' -f2 | cut -d ']' -f1 | sed 's/rabbit@//g' | sed 's/,/, /g'")
            pout = self._send_command(f'echo {out} | sed  "s/\'//g" | sed  "s/ //g"')
        else:
            sys.stderr.write("This RabbitMQ version: $rabbitmq_version is not supported")
            sys.exit(1)
        return pout

    def get_cluster_running_nodes(self, msg_broker : str):
        if(msg_broker == 'rabbitmq'):
            return self.get_rabbitmq_cluster_nodes()
        else:
            self.usage()       
            

    def process(self):
        cmd = "config"
        if(cmd == "config"):
            self.config_sspl()
        else:
            self.usage()

        # Get the version. Output can be 3.3.5 or 3.8.9 or in this format
        mi = self.ts.dbMatch( 'name', 'rabbitmq-server' )
        for h in mi:
            self.rabbitmq_version = bytes.decode(h['version'])
        
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
                self._send_command(f'{consts.CONSUL_PATH}/consul kv put sspl/config/RABBITMQCLUSTER/cluster_nodes {pout}')
                if not self.rmq_cluster_nodes:
                    self._send_command(f'{consts.CONSUL_PATH}/consul kv put sspl/config/RABBITMQCLUSTER/cluster_nodes {self.rmq_cluster_nodes}')
                else:
                    # sed -i "s/cluster_nodes=.*/cluster_nodes=$pout/" $SSPL_CONF
                    self.append_val(consts.file_store_config_path, f'cluster_nodes={pout}', 'cluster_nodes=')
            
        # Skip this step if sspl is being configured for node replacement scenario as consul data is already
        # available on healthy node
        # Updating build requested log level
        if not consts.REPLACEMENT_NODE_ENV_VAR_FILE:
            log_level = None
            with open(f'{self.DIR_NAME}/low-level/files/opt/seagate/sspl/conf/build-requested-loglevel', 'r') as f:
                log_level = f.readline()
            
            if(log_level == "DEBUG" or log_level == "INFO" or log_level == "WARNING" or log_level == "ERROR" or log_level == "CRITICAL"):
                if consts.PRODUCT_NAME == "LDR_R1":
                    self._send_command(f'{consts.CONSUL_PATH}/consul kv put sspl/config/SYSTEM_INFORMATION/log_level {log_level}')
                else:
                    self.append_val(consts.file_store_config_path, f'log_level={log_level}', 'log_level')
            else:
                sys.stderr.write(f"Unexpected log level is requested, '{log_level}'")        

if __name__ == "__main__":
    conf = Config(sys.argv[1:])
    conf.process()
