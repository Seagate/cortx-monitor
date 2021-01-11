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
  Description:   Update SSPL config file for LDR_R2 system
  Purpose    :   SSPL will be initialized using config from sspl.conf
  Usage      :   python3 update_sspl_config.py [-F] [-C] [-N] [-Ru] [-Rp]
 ******************************************************************************
"""

import re
import os
import argparse
from configparser import ConfigParser

from cortx.utils.process import SimpleProcess
from cortx.utils.security.cipher import Cipher


class LoadConfig:

    """ Update sspl config file """

    def __init__(self):
        """ Initialize required config """
        self.rmq_same_pass_sect = ["LOGGINGPROCESSOR",
                                   "RABBITMQEGRESSPROCESSOR",
                                   "RABBITMQINGRESSPROCESSOR"]
        self.common_config_sect = ['system_information',
                                   'storage_enclosure',
                                   'bmc',
                                   'rabbitmq']
        # TODO: Get persistent data from ConfigStore or cortx-utils
        self.persistent_data_file = "/opt/seagate/cortx/sspl/generated_configs"
        self.cluster_id = self._get_result('uuidgen')
        self.node_id = self._get_result('uuidgen')
        self.rmq_encrypted_passwd = ""

        # Initialize config parser
        self.parser = ConfigParser(allow_no_value=True)

    @staticmethod
    def _get_result(cmd):
        """ Execute command and return output """
        result = ""
        out, _, rc = SimpleProcess(cmd).run()
        if rc == 0:
            result = out.decode('utf-8').strip()
        return result

    def sync_persistent_data(self, source, destination):
        """ Update sspl config file with persistent data """
        persistent_data = ""
        if os.path.isfile(source):
            with open(source) as fObj:
                persistent_data = fObj.read().strip()
        result = re.findall(r"cluster_id=(.*)", persistent_data)
        self.cluster_id = result[0] if result else self.cluster_id
        result = re.findall(r"node_id=(.*)", persistent_data)
        self.node_id = result[0] if result else self.node_id
        # Update persistent data file
        persistent_data = f"cluster_id={self.cluster_id}\n" + \
                          f"node_id={self.node_id}\n"
        with open(source, "w") as fObj:
            fObj.write(persistent_data)

    def _encrypt(self, value, service_name):
        """ Encrypt the value using text """
        key=Cipher.generate_key(self.cluster_id, service_name)
        encrypt_pass=Cipher.encrypt(key, value.encode()).decode("utf-8")
        return encrypt_pass

    def sync_config(self, node, config_file, \
                    rmq_user=None, rmq_passwd=None, \
                    primary_mc=None, secondary_mc=None, \
                    primary_mc_port=None, secondary_mc_port=None, \
                    mc_user=None, mc_passwd=None, \
                    bmc_ip=None, bmc_user=None, bmc_passwd=None, \
                    storage_type=None, server_type=None):
        """ Read and update config file """
        self.parser.read(config_file)
        # TODO: Update cluster_id and required passwd using ConfigStore
        if not rmq_passwd:
            self.cluster_id = self.parser.get('SYSTEM_INFORMATION', 'cluster_id')
            rmq_epasswd = self.parser.get('RABBITMQEGRESSPROCESSOR', 'password')
        else:
            rmq_epasswd = self._encrypt(rmq_passwd, "rabbitmq")
        if not bmc_passwd:
            self.cluster_id = self.parser.get('SYSTEM_INFORMATION', 'cluster_id')
            bmc_epasswd = self.parser.get('BMC', 'secret')
        else:
            bmc_epasswd = self._encrypt(bmc_passwd, "bmc")
        if not mc_passwd:
            self.cluster_id = self.parser.get('SYSTEM_INFORMATION', 'cluster_id')
            mc_epasswd = self.parser.get('STORAGE_ENCLOSURE', 'password')
        else:
            mc_epasswd = self._encrypt(mc_passwd, "storage_enclosure")
        # Set store type is 'file' for LDR_R2
        self.parser.set('DATASTORE', 'store_type', 'file')
        # Update same password for required sections
        for section in self.rmq_same_pass_sect:
            self.parser.set(section, "username", rmq_user)
            self.parser.set(section, "password", rmq_epasswd)
        # Update common config
        self.parser.set('STORAGE_ENCLOSURE', 'primary_controller_ip', primary_mc)
        self.parser.set('STORAGE_ENCLOSURE', 'primary_controller_port', primary_mc_port)
        self.parser.set('STORAGE_ENCLOSURE', 'secondary_controller_ip', secondary_mc)
        self.parser.set('STORAGE_ENCLOSURE', 'secondary_controller_port', secondary_mc_port)
        self.parser.set('STORAGE_ENCLOSURE', 'user', mc_user)
        self.parser.set('STORAGE_ENCLOSURE', 'password', mc_epasswd)
        self.parser.set('STORAGE_ENCLOSURE', 'type', storage_type)
        self.parser.set('BMC', 'ip', bmc_ip)
        self.parser.set('BMC', 'user', bmc_ip)
        self.parser.set('BMC', 'secret', bmc_epasswd)
        self.parser.set('SYSTEM_INFORMATION', 'cluster_id', self.cluster_id)
        self.parser.set('SYSTEM_INFORMATION', 'node_id', self.node_id)
        self.parser.set('SYSTEM_INFORMATION', 'kernel_version', self._get_result('uname -r'))
        self.parser.set('SYSTEM_INFORMATION', 'type', server_type)
        with open(config_file, "w") as configFile:
            self.parser.write(configFile)
        self.sync_persistent_data(self.persistent_data_file, config_file)


if __name__ == '__main__':
    argParser = argparse.ArgumentParser(
        usage = "%(prog)s [-h] [-N] [-C] [-Ru] [-Rp] [-A] [-B] \
                    [-Ap] [-Bp] [-U] [-P] [--bmc_ip] [--bmc_user] [--bmc_passwd]",
        formatter_class = argparse.RawDescriptionHelpFormatter)
    argParser.add_argument("-N", "--node", default="srvnode-1", help="Node name")
    argParser.add_argument("-C", "--config_file", default="/etc/sspl.conf", help="Config file path")
    argParser.add_argument("-Ru", "--rmq_user", default="", help="Rabbitmq username")
    argParser.add_argument("-Rp", "--rmq_passwd", default="", help="Rabbitmq password")
    argParser.add_argument("-A", "--primary_mc", default="10.0.0.2", help="Controller-A IP")
    argParser.add_argument("-B", "--secondary_mc", default="10.0.0.3", help="Controller-B IP")
    argParser.add_argument("-Ap", "--primary_mc_port", default="80", help="Controller-A Port")
    argParser.add_argument("-Bp", "--secondary_mc_port", default="80", help="Controller-B Port")
    argParser.add_argument("-U", "--user", default="", help="Controller Username")
    argParser.add_argument("-P", "--passwd", default="", help="Controller Password")
    argParser.add_argument("--bmc_ip", default="", help="BMC IP")
    argParser.add_argument("--bmc_user", default="", help="BMC User")
    argParser.add_argument("--bmc_passwd", default="", help="BMC Password")
    argParser.add_argument("-St", "--storage_type", default="", help="Storage Type")
    argParser.add_argument("-Sr", "--server_type", default="", help="Server Type")
    args = argParser.parse_args()
    sc = LoadConfig()
    if args.rmq_passwd == 'xxxx':
        args.rmq_passwd = ""
    if args.passwd == 'xxxx':
        args.passwd = ""
    if args.bmc_passwd == 'xxxx':
        args.bmc_passwd = ""
    sc.sync_config(node=args.node,
                   config_file=args.config_file,
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
