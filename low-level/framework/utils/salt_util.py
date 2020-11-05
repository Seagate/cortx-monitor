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


'''Module which provides common config information using cortx utils'''

import configparser
from cortx.utils.kvstore.pillar import PillarStorage
import subprocess
import sys

class SaltInterface:
    """
    Interface class to get common config from common pillar using
    Provisioner API
    """
    CLUSTER_KEY = 'cluster'
    CLUSTER_TYPE_KEY = 'type'
    SSPL_KEY = 'sspl'
    DATASTORE_KEY = 'DATASTORE'
    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'
    MINION_ID_KEY = 'salt_minion_id'
    CONSUL_HOST_KEY = 'consul_host'
    CONSUL_PORT_KEY = 'consul_port'

    def __init__(self):
        '''init method'''
        self.node_id = self.get_node_id()
        self.pillar_storage = PillarStorage()
        self._is_single_node = self._is_server_single()
        self.consul_host = self.get_consul_vip()
        self.consul_port = self.get_consul_port()
        self.config = configparser.ConfigParser()

    def get_node_id(self):
        '''Returns salt minion_id using salt config file'''

        _node_id = 'srvnode-1'
        try:
            CMD = ['sudo', 'salt-call', '--local', 'grains.get', 'id', '--output=newline_values_only']
            _result, _err, _ret_code = self.execute_cmd(CMD)
            if _ret_code == 0 and _err.decode('utf-8') == '':
                _node_id = _result.decode('utf-8').rstrip()
            else:
                print(f'salt_util, Failed to read node-id with error : {_err},' + \
                             f'Keeping default value as srvnode-1')
        except Exception as err:
            print(f'salt_util, Failed to read node-id with error: {err},' + \
                             f'Keeping default value as srvnode-1')
        return _node_id

    def _is_server_single(self, _err=None):
        """
        Returns true if single node, false otherwise
        """
        _is_single_node = False

        try:
            if self.pillar_storage.get(f'{self.CLUSTER_KEY}:{self.CLUSTER_TYPE_KEY}') == 'single':
                _is_single_node = True
        except Exception as err:
            print(f'salt_util, Fail to read cluster type with' + \
                             f'this error: {err}, Assuming multi node')
        return _is_single_node

    def is_env_vm(self):
        """
        Returns true if VM env, false otherwise
        """
        is_vm = True
        CMD = "facter is_virtual"
        try:
            subout = subprocess.Popen(CMD, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = subout.stdout.readlines()
            if result == [] or result == "":
                print("Not able to read whether env is vm or not, assuming VM env.")
            else:
                if 'false' in result[0].decode():
                    is_vm = False
        except Exception as e:
            print(f"Error while reading whether env is vm or not, assuming VM env : {e}")
        return is_vm

    def execute_cmd(self, command=[]):
        """
        Executes action using python subprocess module
        and returns the output
        1. output of the command in byte
        2. return_code
        """
        #TODO Handle exception at caller side
        process = subprocess.Popen(command, shell=False, stdout=subprocess.PIPE,\
                                   stderr=subprocess.PIPE)
        _result, _err = process.communicate()
        return _result, _err, process.returncode

    def get_consul_vip(self, _err=None):
        """
        Returns IP used to connect to Consul
        """
        _is_env_vm = self.is_env_vm()
        _is_single_server = self._is_single_node

        # Initialize to localhost
        _consul_vip = "127.0.0.1"

        # Get vip if not a vm or single node, default to localhost otherwise
        if not _is_env_vm or not _is_single_server:
            try:
                _consul_vip = self.pillar_storage.get(f'{self.CLUSTER_KEY}:{self.node_id}:' \
                    + 'network:data_nw:roaming_ip')
            except Exception as err:
                print(f'salt_util, fail to read consul vip with' + \
                                 f'this error: {err}, assuming localhost:' + \
                                f'{_consul_vip} connection')
        return _consul_vip

    def get_consul_port(self, _err=None):
        """
        Returns port used to connect to Consul
        """
        # Initialize to default
        _consul_port = '8500'
        # Read consul port from sspl.sls
        try:
            _consul_port = self.pillar_storage.get(f'{self.SSPL_KEY}:{self.DATASTORE_KEY}:consul_port')
        except Exception as err:
            print(f'salt_util, Fail to read consul port with' + \
                             f'this error: {err}, Assuming the port: {_consul_port}')
        return _consul_port

    def update_config_file(self, conf_file):
        """
        Writes salt minion id, consul host and port to conf file
        """
        try:
            # Read the config
            self.config.read(conf_file)
            # Update required values
            if self.SYSTEM_INFORMATION_KEY in self.config.sections():
                self.config[self.SYSTEM_INFORMATION_KEY][self.MINION_ID_KEY] = self.node_id
            else:
                print(f'salt_util, Failed to update minion id in {conf_file}')
            if self.DATASTORE_KEY in self.config.sections():
                self.config[self.DATASTORE_KEY][self.CONSUL_HOST_KEY] = self.consul_host
                self.config[self.DATASTORE_KEY][self.CONSUL_PORT_KEY] = self.consul_port
            else:
                print(f'salt_util, Failed to update consul host and port in {conf_file}')
            # Write the config to file
            with open(conf_file, 'w') as configfile:
                self.config.write(configfile)
        except Exception as err:
            print(f'salt_util, Failed to update conf_file {conf_file} with error : {err}')


if __name__ == "__main__":
    conf_file = sys.argv[1]
    salt_util = SaltInterface()
    salt_util.update_config_file(conf_file)
