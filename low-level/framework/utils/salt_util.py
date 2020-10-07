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


import errno

try:
    from service_logging import logger
    from utility import Utility
except Exception as err:
    from framework.utils.service_logging import logger
    from framework.utils.utility import Utility


class SaltInterface:
    """
    Interface class to get common config from common pillar using
    Provisioner API
    """

    __instance = None
    SALT_FILE = '/etc/salt/minion_id'

    CLUSTER_KEY = 'cluster'
    CLUSTER_TYPE_KEY = 'type'
    SSPL_KEY = 'sspl'
    DATASTORE_KEY = 'DATASTORE'

    def __init__(self):
        '''init method'''
        if SaltInterface.__instance is None:
            self.utility = Utility()
            self.pillar_info = None
            self.node_id = None or self.get_node_id()
            _result, _err, _ret_code = \
                    self.utility.execute_cmd(['sudo', 'provisioner', 'pillar_get'])
            _err = _err.decode("utf-8").rstrip()
            if _ret_code == 0 and _err == '':
                self.pillar_info = eval(_result.decode("utf-8").rstrip())
            self._is_single_node = None or self._is_server_single(_err)
            self.consul_host = None or self.get_consul_vip(_err)
            self.consul_port = None or self.get_consul_port(_err)
            SaltInterface.__instance = self

    @staticmethod
    def get_singleton_instance():
        '''Returns an instance of this class'''
        if SaltInterface.__instance is None:
            SaltInterface()
        return SaltInterface.__instance

    @staticmethod
    def get_node_id():
        '''Returns salt minion_id using salt config file'''

        _node_id = 'srvnode-1'
        try:
            with open(SaltInterface.SALT_FILE, 'r') as salt_file:
                _node_id = salt_file.read().rstrip()
            if _node_id is None or _node_id == '':
                _node_id = 'srvnode-1'
            logger.info(f'salt_util, Server minion ID: {_node_id}')
        except OSError as err:
            if err.errno == errno.ENOENT:
                logger.error(
                    f'Problem occured while reading from salt file. \
                     File path: {SaltInterface.SALT_FILE} does not exist')
            elif err == errno.EACCES:
                logger.error(
                    f'Problem occured while reading from salt file. \
                     Permission issue while reading from: {SaltInterface.SALT_FILE}')
            else:
                logger.error(
                    f'Problem occured while reading from salt file with \
                     the issue: {err}')
        except Exception as err:
            logger.warning(f'salt_util, Fail to read node-id with error: {err}, \
                             Keeping default value as srvnode-1')
        return _node_id

    def _is_server_single(self, _err=None):
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
                logger.info(f'salt_util, Node type: {_is_single_node}')
            else:
                logger.warning(f'salt_util, Fail to read cluster type with \
                                 this error: {_err}. Assuming single node')
        except KeyError as key_err:
            logger.warning(f'salt_util, Fail to read cluster type with \
                             this key error: {key_err}, Assuming single node')
        except Exception as err:
            logger.warning(f'salt_util, Fail to read cluster type with \
                             this error: {err}, Assuming single node')
        return _is_single_node

    def get_consul_vip(self, _err=None):
        """
        Returns IP used to connect to Consul
        """
        _is_env_vm = self.utility.is_env_vm()
        _is_single_server = self._is_single_node

        # Initialize to localhost
        _consul_vip = "127.0.0.1"

        # Get vip if not a vm or single node, default to localhost otherwise
        if not _is_env_vm or not _is_single_server:
            try:
                if self.pillar_info is not None:
                    _consul_vip = \
                        self.pillar_info[self.node_id][self.CLUSTER_KEY][self.node_id]\
                        ['network']['data_nw']['roaming_ip']
                    logger.debug(f'salt_util, consul VIP: {_consul_vip}')
                else:
                    logger.warning(f'salt_util, Fail to read consul VIP with \
                                     this error: {_err}, Assuming localhost: \
                                     {_consul_vip} connection')
            except KeyError as key_err:
                logger.warning(f'salt_util, fail to read consul vip with \
                                 this key error: {key_err}, assuming localhost: \
                                 {_consul_vip} connection')
            except Exception as err:
                logger.warning(f'salt_util, fail to read consul vip with \
                                 this error: {err}, assuming localhost: \
                                 {_consul_vip} connection')
        return _consul_vip

    def get_consul_port(self, _err=None):
        """
        Returns port used to connect to Consul
        """
        # Initialize to default
        _consul_port = '8500'
        # Read consul port from sspl.sls
        try:
            if self.pillar_info is not None:
                data_store_config = \
                    self.pillar_info[self.node_id][self.SSPL_KEY][self.DATASTORE_KEY]
                if data_store_config is not None:
                    _consul_port = data_store_config['consul_port']
                logger.info(f'salt_util, consul port: {_consul_port}')
            else:
                logger.warning(f'salt_util, Fail to read consul port with \
                                 this error: {_err}, Assuming the port: {_consul_port}')
        except KeyError as key_err:
            logger.warning(f'salt_util, Fail to read consul port with \
                             this error: {key_err}, Assuming the port: {_consul_port}')
        except Exception as err:
            logger.warning(f'salt_util, Fail to read consul port with \
                             this error: {err}, Assuming the port: {_consul_port}')
        return _consul_port


salt_util = SaltInterface.get_singleton_instance()
if salt_util:
    node_id = salt_util.node_id
    consulhost = salt_util.consul_host
    consulport = salt_util.consul_port
