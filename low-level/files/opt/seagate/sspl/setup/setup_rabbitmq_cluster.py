#!/usr/bin/python3.6

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

###############################################
# Joins nodes in current node Rabbitmq cluster
###############################################

import sys
import socket
import argparse
import re

# using cortx library
from framework.base.global_config import GlobalConf
from cortx.utils.process import SimpleProcess
from .setup_error import SetupError

localhost_fqdn = socket.getfqdn().split('.')[0]


class RMQClusterConfiguration:

    """Use RabbitMQ configuration to form RabbitMQ cluster."""

    SECTION = "RABBITMQCLUSTER"
    CLUSTER_NODES = "cluster_nodes"
    ERLANG_COOKIE = "erlang_cookie"
    RABBITMQCTL = "/usr/sbin/rabbitmqctl"
    ERLANG_COOKIE_PATH = "/var/lib/rabbitmq/.erlang.cookie"

    def __init__(self, nodes):
        self._global_conf = GlobalConf()
        self.requested_nodes = nodes

    def setup_rabbitmq(self):
        command = "systemctl start rabbitmq-server"
        self._send_command(command)
        self._open_rabbitmq_ports()
        self._copy_erlang_cookie()

    def _send_command(self, command, fail_on_error=True):
        """
        Execute command and retrun response
        Parameters:
            command: shell command to execute
            fail_on_error: Set to False will ignore command failure
        """
        print(f"Executing: {command}")
        output, error, returncode = SimpleProcess(command).run()
        if fail_on_error and returncode != 0:
            raise SetupError(returncode,
                             "ERROR: Command '%s' failed with error\n  %s",
                             command,
                             error)
        return output.decode('utf-8')

    def _open_rabbitmq_ports(self):
        """
        Enable firewall and required tcp ports for RabbitMQ
        """
        command = "systemctl start firewalld"
        self._send_command(command)
        command = "firewall-cmd --zone=public --permanent --add-port=4369/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --zone=public --permanent --add-port=25672/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --zone=public --permanent --add-port=25672/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --zone=public --permanent --add-port=5671-5672/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --zone=public --permanent --add-port=15672/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --zone=public --permanent --add-port=15672/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --zone=public --permanent --add-port=61613-61614/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --zone=public --permanent --add-port=1883/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --zone=public --permanent --add-port=8883/tcp"
        self._send_command(command, fail_on_error=False)
        command = "firewall-cmd --reload"
        self._send_command(command)

    def _copy_erlang_cookie(self):
        """
        Read erlang cookie and update cookie file
        """
        print('Creating erlang cookie...')
        command = 'systemctl stop rabbitmq-server'
        self._send_command(command)
        # all rabbitmq servers needs to have same erlang cookie for clustering.
        cookie_value = self._global_conf.fetch_sspl_config(qwery_string="%s>%s" %
                                                (self.SECTION, self.ERLANG_COOKIE))
        command = f'chmod +w {self.ERLANG_COOKIE_PATH}'
        self._send_command(command)
        command = f'echo "{cookie_value}" > {self.ERLANG_COOKIE_PATH}'
        self._send_command(command)
        command = f'chmod -w {self.ERLANG_COOKIE_PATH}'
        self._send_command(command)
        # restarting to make sure it starts in case it is not stopped already.
        command = 'systemctl restart rabbitmq-server'
        self._send_command(command)
        print('Done creating erlang cookie')

    def reset_rmq_cluster(self):
        """
        Removes nodes from current cluster setup that are not matching with requested nodes.
        """
        if self.requested_nodes and isinstance(self.requested_nodes, str):
            requested_nodes = self.requested_nodes.strip().split(",")
        command = "rabbitmqctl cluster_status"
        response = self._send_command(command)
        cluster_nodes_fqdn = set(re.findall(r".*rabbit@([\w-]+).*", response, re.M|re.I))
        req_nodes_fqdn = {node.split(".")[0] for node in requested_nodes}
        for cln_fqdn in cluster_nodes_fqdn:
            if cln_fqdn not in req_nodes_fqdn:
                # Can not remove clustering(primary) node node from cluster
                if cln_fqdn == localhost_fqdn:
                    continue
                print(f"Removing rabbit@{cln_fqdn} from cluster setup..")
                command = "rabbitmqctl stop_app"
                self._send_command(command)
                command = "rabbitmqctl reset"
                self._send_command(command)
                command = "rabbitmqctl start_app"
                self._send_command(command)
                command = "systemctl restart rabbitmq-server"
                self._send_command(command)
                self._copy_erlang_cookie()

    def _update_rmq_cluster_nodes_in_config(self):
        """
        Updates RMQ cluster nodes in sspl config file
        """
        self._global_conf.set_sspl_config(request="%s>%s" %
                 (self.SECTION, self.CLUSTER_NODES), value = self.requested_nodes)
        print("Successfully updated RMQ cluster nodes in config.")

    def make_rmq_cluster(self):
        """
        Creates RabbitMQ cluster using given nodes
        """
        if self.requested_nodes and isinstance(self.requested_nodes, str):
            requested_nodes = self.requested_nodes.strip().split(",")
        # Create RMQ cluster only with requested nodes
        print(f'Joining {requested_nodes} to RabbitMQ cluster...')
        clustered = False
        node_fqdn = None
        for node_fqdn in requested_nodes:
            if node_fqdn != localhost_fqdn and not clustered:
                command = "%s stop_app" % self.RABBITMQCTL
                response = self._send_command(command)
                print("Stopping app: %s" % response)
                command = f'{self.RABBITMQCTL} join_cluster rabbit@{node_fqdn}'
                response = self._send_command(command, fail_on_error=False)
                print(f"Join response: {response}")
                if 'Error:' in response:
                    print(f'WARNING: Unable to connect to {node_fqdn} error: {response}')
                    print('Re-trying another node...')
                else:
                    clustered = True
                command = f"{self.RABBITMQCTL} start_app"
                response = self._send_command(command)
                print(f"Added '{node_fqdn}' to rabbitmq cluster")
                break
        if clustered:
            print(f'RabbitMQ clustering is successfully formed with nodes {requested_nodes}.')
            self._update_rmq_cluster_nodes_in_config()
        else:
            if node_fqdn is not None and node_fqdn != localhost_fqdn:
                print("ERROR: Unable to clustering with any node. \
                    Please check the node health or configuration.")
                sys.exit()
            else:
                print(f"RabbitMQ cluster is formed only with current host: {node_fqdn}")

    def process(self):
        if not self.requested_nodes:
            print("Cluster setup on this single node setup is ignored. " + \
                  "Clustering requires joining nodes as argument.")
            return
        # Setup RMQ config - rabbitmq ports and erlang cookie
        self.setup_rabbitmq()

        # Reset previous cluster setup
        self.reset_rmq_cluster()

        # Add nodes in rabbitmq cluster
        self.make_rmq_cluster()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--nodes", help="""Comma separated cluster nodes. This is optional.
                                                Default value is fqdn of the localhost""",
                                        action="store", default=localhost_fqdn)
    args = parser.parse_args()
    nodes = args.nodes.replace(" ", "")
    RMQClusterConfiguration(nodes).process()
