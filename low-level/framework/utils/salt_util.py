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


'''Module which provides common config information using Provisioner API'''


try:
    from service_logging import logger
    from utility import Utility
except Exception as err:
    from framework.utils.service_logging import logger
    from framework.utils.utility import Utility


class CommonConfig:
    """
    Interface class to get common config from common pillar using
    Provisioner API
    """

    __instance = None
    CLUSTER_KEY = 'cluster'
    CLUSTER_TYPE_KEY = 'type'
    SSPL_KEY = 'sspl'
    DATASTORE_KEY = 'DATASTORE'

    def __init__(self):
        '''init method'''
        if CommonConfig.__instance is None:
            self.utility = Utility()
            self.pillar_info = None
            _result, _err, _ret_code = \
                    self.utility.execute_cmd(['sudo', 'provisioner', 'pillar_get'])
            _err = _err.decode("utf-8").rstrip()
            if _ret_code == 0 and _err is '':
                self.pillar_info = eval(_result.decode("utf-8").rstrip())
            self.node_id = None or self.get_node_id()
            self._is_single_node = None or self._is_single_node()
            self.consul_host = None or self.get_consul_vip()
            self.consul_port = None or self.get_consul_port()
            CommonConfig.__instance = self

    @staticmethod
    def get_singleton_instance():
        '''Returns an instance of this class'''
        if CommonConfig.__instance is None:
            CommonConfig()
        return CommonConfig.__instance

    @staticmethod
    def get_node_id():
        '''Returns salt minion_id using salt config file'''

        _node_id = 'srvnode-1'
        try:
            with open('/etc/salt/minion_id', 'r') as salt_file:
                _node_id = salt_file.read()
            if _node_id is not None:
                _node_id = 'srvnode-1'
        except Exception as err:
            logger.warning(f'sspl_constants, Fail to read node-id with error: {err}, \
                             Keeping default value as srvnode-1')
            _node_id = 'srvnode-1'
        return _node_id

    def _is_single_node(self):
        """
        Returns true if single node, false otherwise
        """
        _is_single_node = False
        try:
            if self.pillar_info:
                cluster_type = \
                    self.pillar_info[self.node_id][self.CLUSTER_KEY][self.CLUSTER_TYPE_KEY]
                if cluster_type is not None and cluster_type.lower() == 'single':
                    _is_single_node = True
            else:
                logger.warning(f'sspl_constants, Fail to read cluster type with \
                               this error: {_err}, Assuming single node')
        except Exception as err:
            logger.warning(f'sspl_constants, Fail to read cluster type with \
                               this error: {err}, Assuming single node')
        logger.info(f'sspl_constants, Node type: {_is_single_node}')
        return _is_single_node

    def get_consul_vip(self):
        """
        Returns IP used to connect to Consul
        """
        _is_env_vm = self.utility.is_env_vm()
        _is_single_node = self._is_single_node
        # Initialize to localhost
        _consul_vip = "127.0.0.1"
        # Get vip if not a vm or single node, default to localhost otherwise if not _is_env_vm and not _is_single_node:
        try:
            if self.pillar_info is not None:
                data_store_config = \
                    self.pillar_info[self.node_id][self.SSPL_KEY][self.DATASTORE_KEY]
                if data_store_config is not None:
                    _consul_vip = data_store_config['consul_host']
            else:
                logger.warning(f'sspl_constants, Fail to read consul VIP with \
                                 this error: {_err}, Assuming localhost: \
                                 {_consul_vip} connection')
        except Exception as err:
            logger.warning(f'sspl_constants, Fail to read consul VIP with \
                             this error: {err}, Assuming localhost: \
                             {_consul_vip} connection')
        logger.info(f'sspl_constants, consul VIP: {_consul_vip}')
        return _consul_vip

    def get_consul_port(self):
        """
        Returns port used to connect to Consul
        """
        # Initialize to default
        consul_port = '8500'
        # Read consul port from sspl.sls
        try:
            if self.pillar_info is not None:
                data_store_config = \
                    self.pillar_info[self.node_id][self.SSPL_KEY][self.DATASTORE_KEY]
                if data_store_config is not None:
                    consul_vip = data_store_config['consul_port']
            else:
                logger.warning(f'sspl_constants, Fail to read consul VIP port with \
                                 this error: {_err}, Assuming localhost: {consul_port} connection')
        except Exception as err:
            logger.warning(f'sspl_constants, Fail to read consul VIP with \
                             this error: {err}, Assuming localhost: {consul_vip} connection')
        logger.info(f'sspl_constants, consul port: {consul_port}')
        return consul_port


comm_conf = CommonConfig.get_singleton_instance()
if comm_conf:
    node_id = comm_conf.node_id
    consulhost = comm_conf.consul_host
    consulport = comm_conf.consul_port
