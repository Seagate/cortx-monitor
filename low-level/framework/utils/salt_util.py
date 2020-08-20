import salt.client

try:
    from utility import Utility
    from service_logging import logger
except Exception as e:
    from framework.utils.utility import Utility
    from framework.utils.service_logging import logger

class SaltInterface:
    """
    Interface class to run salt commands and get values from cluster.sls
    """

    def __init__(self):
        self._client = salt.client.LocalClient()
        self.GRAINS_GET_NODE_CMD = "salt-call grains.get id --output=newline_values_only"
        self.MINION_GET_NODE_CMD = "cat /etc/salt/minion_id"
        self.utility = Utility()

    def get_node_id(self):
        node_key = 'srvnode-1'
        try:
            subout = self._client.cmd('*', 'cmd.run', [self.GRAINS_GET_NODE_CMD])
            result = list(subout.keys())
            if result == [] or result == "":
                logger.warning(f"Command '{self.GRAINS_GET_NODE_CMD}' failed to fetch grain id or hostname.")
                subout = self._client.cmd('*', 'cmd.run', [self.MINION_GET_NODE_CMD])
                result = list(subout.keys())
                if result == [] or result == "":
                    logger.warning(f"Command '{self.MINION_GET_NODE_CMD}' failed to fetch minion id or hostname.")
                    logger.warning("Using node_id ('srvnode-1') as we are not able to fetch it from hostname command.")
                    node_key = 'srvnode-1'
                else:
                    node = result[0]
                    node_key = subout[node]
            else:
                node = result[0]
                node_key = subout[node]
        except Exception as e:
            logger.warning(f"Can't read node id, using 'srvnode-1' : {e}")
        return node_key

    def is_single_node(self):
        """
        Returns true if single node, false otherwise
        """
        is_single_node = True
        try:
            SALT_CMD = "sudo salt-call pillar.get cluster:type --output=newline_values_only"
            subout = self._client.cmd('*', 'cmd.run', [SALT_CMD])
            result = list(subout.keys())
            if result == [] or result == "":
                logger.warning("Cluster type fetch failed, assuming single node setup.")
            else:
                node = result[0]
                node_val = subout[node]
                if node_val != "single":
                    is_single_node = False
        except Exception as e:
            logger.warning(f"Cluster type read failed, assuming single node setup : {e}")
        return is_single_node

    def get_consul_vip(self, node_name):
        """
        Returns IP used to connect to Consul
        """
        is_env_vm = self.utility.is_env_vm()
        is_single_node = self.is_single_node()
        # Initialize to localhost
        consul_vip = "127.0.0.1"
        # Get vip if not a vm or single node, default to localhost otherwise
        if not is_env_vm and not is_single_node:
            # Read vip from cluster.sls
            try:
                SALT_CMD = f"sudo salt-call pillar.get cluster:{node_name}:network:data_nw:roaming_ip --output=newline_values_only"
                subout = self._client.cmd('*', 'cmd.run', [SALT_CMD])
                result = list(subout.keys())
                if result == [] or result == "":
                    logger.warning("Cluster VIP fetch failed, using localhost to connect to Consul.")
                else:
                    node = result[0]
                    consul_vip = subout[node]
            except Exception as e:
                logger.warning(f"Cluster VIP read failed, using localhost to connect to Consul : {e}")
        return consul_vip

    def get_consul_port(self):
        """
        Returns port used to connect to Consul
        """
        # Initialize to default
        consul_port = '8500'
        # Read consul port from sspl.sls
        try:
            SALT_CMD = f"sudo salt-call pillar.get sspl:DATASTORE:consul_port --output=newline_values_only"
            subout = self._client.cmd('*', 'cmd.run', [SALT_CMD])
            result = list(subout.keys())
            if result == [] or result == "":
                logger.warning("Consul Port fetch failed, using 8500 to connect.")
            else:
                node = result[0]
                consul_port = subout[node]
        except Exception as e:
            logger.warning(f"Consul Port read failed, using 8500 to connect : {e}")
        return consul_port

salt_int = SaltInterface()
node_id = salt_int.get_node_id()
consulhost = salt_int.get_consul_vip(node_id)
consulport = salt_int.get_consul_port()
