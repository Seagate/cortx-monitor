#!/usr/bin/env python3

# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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

"""
 ******************************************************************************
  Description:   Parse config file and arguments to set common & SSPL config
  Purpose    :   To feed sspl and common configuration to consul
  Usage      :   python3 feed_sspl_conf_to_consul.py [-F] [-C] [-N] [-Ru] [-Rp]
 ******************************************************************************
"""

import re
import os
import sys
import consul
import argparse
from configobj import ConfigObj

from cortx.utils.process import SimpleProcess

CONSUL_HOST = '127.0.0.1'
CONSUL_PORT = '8500'


class LoadConfig:

    def __init__(self):
        """ Establish consul connection
        """
        host = os.getenv('CONSUL_HOST', CONSUL_HOST)
        port = os.getenv('CONSUL_PORT', CONSUL_PORT)
        self.consul_conn = consul.Consul(host=host, port=port)
        self.rmq_same_pass_sect = ["LOGGINGPROCESSOR",
                                   "RABBITMQEGRESSPROCESSOR",
                                   "RABBITMQINGRESSPROCESSOR"]
        self.common_config_sect = ['system_information',
                                   'storage_enclosure',
                                   'bmc',
                                   'rabbitmq']
        # TODO: Get persistent data from ConfigStore or cortx-utils
        self.persistent_data_file = "/opt/seagate/cortx/sspl/generated_configs"
        self.cluster_id = ""
        self.node_id = ""
        self.rmq_encrypted_passwd = ""

    def _get_result(self, cmd):
        """ Execute command and return output
        """
        result = ""
        out, _, rc = SimpleProcess(cmd).run()
        if rc == 0:
            result = out.decode('utf-8').strip()
        return result

    def _insert_nested_dict_to_consul(self, v, prefix=''):
        """ Parse v and insert kv in consul
        """
        if isinstance(v, dict):
            for k, v2 in v.items():
                p2 = "{}/{}".format(prefix, k)
                self._insert_nested_dict_to_consul(v2, p2)
        elif isinstance(v, list):
            for i, v2 in enumerate(v):
                p2 = "{}/{}".format(prefix, i)
                self._insert_nested_dict_to_consul(v2, p2)
        else:
            if self.consul_conn is not None:
                self.consul_conn.kv.put(prefix, str(v))
            else:
                print('Consul connection issue, consul_conn is None. Exiting..')
                sys.exit()

    def set_config(self, component, node, config_file):
        """ Read config file and insert configs in consul
        """
        try:
            if self.consul_conn is None:
                raise Exception(f"Failed to establish connection to {CONSUL_HOST}:{CONSUL_PORT}")
        except Exception as cerror:
            print("Error in connecting consul | consul: {}".format(cerror))
            print("Exiting...")
            sys.exit(os.EX_USAGE)
        else:
            parser = ConfigObj(config_file, list_values=False)
            # Remove duplicate configs
            if 'STORAGE_ENCLOSURE' in parser.sections:
                 del parser['STORAGE_ENCLOSURE']
            elif 'BMC' in parser.sections:
                del parser['BMC']
            elif 'SYSTEM_INFORMATION' in parser.sections:
                if 'node_id' in parser['SYSTEM_INFORMATION'].keys():
                    del parser['SYSTEM_INFORMATION']['node_id']
            # Insert config
            prefix = component.lower() + '/config/'
            for k, v in parser.items():
                if k.lower() in self.common_config_sect:
                    self._insert_nested_dict_to_consul(v, prefix=k.lower())
                k = prefix + k
                self._insert_nested_dict_to_consul(v, prefix=k)
            # TODO: Get common way of fetching cluster_id, node_id and RMQ password
            persistent_data = ""
            if os.path.isfile(self.persistent_data_file):
                with open(self.persistent_data_file) as fObj:
                    persistent_data = fObj.read().strip()
            if persistent_data:
                result = re.findall(r"cluster_id=(.*)", persistent_data)
                self.cluster_id = result[0] if result else "001"
                result = re.findall(r"node_id=(.*)", persistent_data)
                self.node_id = result[0] if result else "001"
                result = re.findall(r"rmq_encrypted_passwd=(.*)", persistent_data)
                self.rmq_encrypted_passwd = result[0] if result else ""
            else:
                print("WARN: Persistent cluster_id, node_id and RMQ encrypted \
                       password not found. Generating new value of them..")
                cluster_id = self._get_result('consul kv get system_information/cluster_id')
                self.cluster_id = cluster_id  or self._get_result('uuidgen')
                node_id = self._get_result(f'consul kv get system_information/{node}/node_id')
                self.node_id = node_id or self._get_result('uuidgen')

    def sync_config(self, node, component=None, rmq_user=None, rmq_passwd=None,\
                    primary_mc=None, secondary_mc=None, primary_mc_port=None, secondary_mc_port=None,\
                    mc_user=None, mc_passwd=None, bmc_ip=None, bmc_user=None, bmc_passwd=None,\
                    storage_type=None, server_type=None):
        parser = ConfigObj(list_values=False)
        # Include common configuration
        parser['SYSTEM_INFORMATION'] = {
            'kernel_version': self._get_result('uname -r'),
            'cluster_id': self.cluster_id,
            node: {'node_id': self.node_id},
            'type': server_type or self._get_result(
                'consul kv get system_information/type')
        }
        # Storage enclosure information
        parser['STORAGE_ENCLOSURE'] = {
            'controller': {
                'user': mc_user or self._get_result(
                        'consul kv get storage_enclosure/controller/user'),
                'password': mc_passwd or self._get_result(
                        'consul kv get storage_enclosure/controller/password'),
                'primary_mc': {
                    'ip':  primary_mc or self._get_result(
                        'consul kv get storage_enclosure/controller/primary_mc/ip'),
                    'port': primary_mc_port or self._get_result(
                        'consul kv get storage_enclosure/controller/primary_mc/port')
                },
                'secondary_mc': {
                    'ip': secondary_mc or self._get_result(
                        'consul kv get storage_enclosure/controller/secondary_mc/ip'),
                    'port': secondary_mc_port or self._get_result(
                        'consul kv get storage_enclosure/controller/secondary_mc/port')
                }
            },
            'type': storage_type or self._get_result(
                'consul kv get storage_enclosure/type'),
        }
        # BMC information
        parser['BMC'] = { node: {
                            'ip': bmc_ip or self._get_result(f'consul kv get bmc/{node}/ip'),
                            'user': bmc_user or self._get_result(f'consul kv get bmc/{node}/user'),
                            'secret': bmc_passwd or self._get_result(f'consul kv get bmc/{node}/secret')
                            }
                        }
        # Update same password for required sections
        if rmq_passwd:
            self.rmq_encrypted_passwd = rmq_passwd
        for section in self.rmq_same_pass_sect:
            parser[section] = {"username": rmq_user}
            parser[section] = {"password": self.rmq_encrypted_passwd}
        # Insert config data
        prefix = component.lower() + '/config/'
        for k, v in parser.items():
            if k.lower() in self.common_config_sect:
                self._insert_nested_dict_to_consul(v, prefix=k.lower())
            k = prefix + k
            self._insert_nested_dict_to_consul(v, prefix=k)
        # Update persistent data file
        persistent_data = f"cluster_id={self.cluster_id}\n" + \
                          f"node_id={self.node_id}\n" + \
                          f"rmq_encrypted_passwd={self.rmq_encrypted_passwd}"
        with open(self.persistent_data_file, "w") as fObj:
            fObj.write(persistent_data)
        print(persistent_data)


if __name__ == '__main__':
    argParser = argparse.ArgumentParser(
        usage = "%(prog)s [-h] [-F] [-C] [-N] [-Ru] [-Rp] [-A] [-B] \
                    [-Ap] [-Bp] [-U] [-P] [--bmc_ip] [--bmc_user] [--bmc_passwd]",
        formatter_class = argparse.RawDescriptionHelpFormatter)
    argParser.add_argument("-F", "--config_file", default="/etc/sspl.conf", help="Config file path")
    argParser.add_argument("-C", "--component", default="sspl", help="Keys will be stored with this prefix")
    argParser.add_argument("-N", "--node", default="srvnode-1", help="Node name")
    argParser.add_argument("-Ru", "--rmq_user", default="", help="Rabbitmq username")
    argParser.add_argument("-Rp", "--rmq_passwd", default="", help="Rabbitmq password")
    argParser.add_argument("-A", "--primary_mc", default="", help="Controller-A IP")
    argParser.add_argument("-B", "--secondary_mc", default="", help="Controller-B IP")
    argParser.add_argument("-Ap", "--primary_mc_port", default="", help="Controller-A Port")
    argParser.add_argument("-Bp", "--secondary_mc_port", default="", help="Controller-B Port")
    argParser.add_argument("-U", "--user", default="", help="Controller Username")
    argParser.add_argument("-P", "--passwd", default="", help="Controller Password")
    argParser.add_argument("--bmc_ip", default="", help="BMC IP")
    argParser.add_argument("--bmc_user", default="", help="BMC User")
    argParser.add_argument("--bmc_passwd", default="", help="BMC Password")
    argParser.add_argument("-St", "--storage_type", default="", help="Storage Type")
    argParser.add_argument("-Sr", "--server_type", default="", help="Server Type")
    args = argParser.parse_args()
    sc = LoadConfig()
    # Load configs in consul
    sc.set_config(component=args.component.lower(),
                  node=args.node,
                  config_file=args.config_file)
    sc.sync_config(component=args.component.lower(),
                   node=args.node,
                   rmq_user=args.rmq_user,
                   rmq_passwd=args.rmq_passwd,
                   mc_user=args.user,
                   mc_passwd=args.passwd,
                   primary_mc=args.primary_mc,
                   secondary_mc=args.secondary_mc,
                   primary_mc_port=args.primary_mc_port,
                   secondary_mc_port=args.secondary_mc_port,
                   bmc_ip=args.bmc_ip,
                   bmc_user=args.bmc_user,
                   bmc_passwd=args.bmc_passwd,
                   storage_type=args.storage_type,
                   server_type=args.server_type)
