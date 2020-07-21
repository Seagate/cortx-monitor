#!/usr/bin/env python3
"""
 ****************************************************************************
 Filename:          sspl_fetch_config_from_salt.py
 Description:       Getting config data from salt API and feeding to consul
 Creation Date:     02/26/2020
 Author:            Amol Shinde

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os
import sys
import salt.client
import consul
from configparser import ConfigParser
from sspl_constants import (component, salt_provisioner_pillar_sls, CONSUL_HOST, CONSUL_PORT,salt_uniq_attr_per_node,
    salt_uniq_passwd_per_node, COMMON_CONFIGS, OperatingSystem,enabled_products, SSPL_CONFIGS, setups, DATA_PATH,NODE_ID,
    SITE_ID, RACK_ID, SYSLOG_HOST, SYSLOG_PORT,node_key_id)


class SaltConfig(object):

    def __init__(self):
        self.consul_conn = None
        super().__init__()

    def _insert_nested_dict_to_consul(self, v, prefix=''):
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
                print("Inserting common config {}".format(prefix))
                self.consul_conn.kv.put(prefix, str(v))
            else:
                print('Consul connection issue, consul_conn is None. Exiting..')
                sys.exit()

    def sync_sspl_config(self):
        # read stoarge_enclosure.sls
        new_enclosure_conf = salt.client.Caller().function('pillar.get', 'storage_enclosure')
        self._insert_nested_dict_to_consul(new_enclosure_conf, prefix='sspl/config/STORAGE_ENCLOSURE')

        # read stoarge rabbitmq.sls
        new_rabbitmqcluster_conf = salt.client.Caller().function('pillar.get', 'rabbitmq')
        str_keys = [k for k,v in new_rabbitmqcluster_conf.items() if isinstance(v, str)]
        for k in str_keys:
            if k == 'cluster_nodes':
                self.consul_conn.kv.put(component + '/' + 'RABBITMQCLUSTER' + '/' + k, new_rabbitmqcluster_conf[k])
            elif k == 'erlang_cookie':
                self.consul_conn.kv.put(component + '/' + 'RABBITMQCLUSTER' + '/' + k, new_rabbitmqcluster_conf[k])

        # read bmc config
        BMC_CONFIG = salt.client.Caller().function('pillar.get', f'cluster:{node_key_id}:bmc')
        for k,v in BMC_CONFIG.items():
            if k == 'ip':
                self.consul_conn.kv.put(component + '/' + f'BMC/{node_key_id}' + '/' + k, v)
            elif k == 'user':
                self.consul_conn.kv.put(component + '/' + f'BMC/{node_key_id}' + '/' + k, v)
            elif k == 'secret':
                self.consul_conn.kv.put(component + '/' + f'BMC/{node_key_id}' + '/' + k, v)

    def insert_dev_common_config(self, product):
        try:
            print("inserting common config for DEV environment")
            sys_info_default_data = {
                "operating_system": OperatingSystem.RHEL7.value,
                "product": product,
                "setup": setups[0],
                "data_path": DATA_PATH,
                f"{node_key_id}/node_id": NODE_ID,
                "site_id": SITE_ID,
                "rack_id": RACK_ID,
                "syslog_host": SYSLOG_HOST,
                "syslog_port": SYSLOG_PORT
            }
            self._insert_nested_dict_to_consul(sys_info_default_data, prefix='system_information')

            # read stoarge_enclosure.sls
            new_enclosure_conf = salt.client.Caller().function('pillar.get', 'storage_enclosure')
            self._insert_nested_dict_to_consul(new_enclosure_conf, prefix='storage_enclosure')

            # read stoarge rabbitmq.sls
            new_rabbitmqcluster_conf = salt.client.Caller().function('pillar.get', 'rabbitmq')
            str_keys = [k for k,v in new_rabbitmqcluster_conf.items() if isinstance(v, str)]
            for k in str_keys:
                if k == 'cluster_nodes':
                    self.consul_conn.kv.put('rabbitmq/cluster_nodes', new_rabbitmqcluster_conf[k])
                elif k == 'erlang_cookie':
                    self.consul_conn.kv.put('rabbitmq/erlang_cookie', new_rabbitmqcluster_conf[k])

            BMC_CONFIG = salt.client.Caller().function('pillar.get', f'cluster:{node_key_id}:bmc')
            for k,v in BMC_CONFIG.items():
                if k == 'ip':
                    self.consul_conn.kv.put(f'bmc/{node_key_id}/ip', v)
                elif k == 'user':
                    self.consul_conn.kv.put(f'bmc/{node_key_id}/user', v)
                elif k == 'secret':
                    self.consul_conn.kv.put(f'bmc/{node_key_id}/secret', v)

        except Exception as serror:
            print("Error in connecting salt | consul: {}".format(serror))
            print("Exiting ...")
            sys.exit(os.EX_USAGE)

    def set_config(self):
        try:
            new_conf = salt.client.Caller().function('pillar.get', salt_provisioner_pillar_sls)
            host = os.getenv('CONSUL_HOST', CONSUL_HOST)
            port = os.getenv('CONSUL_PORT', CONSUL_PORT)
            self.consul_conn = consul.Consul(host=host, port=port)

            # for the pattern key : 'value'
            str_keys = [k for k,v in new_conf.items() if isinstance(v, str)]
            for k in str_keys:
                self.consul_conn.kv.put(component + '/' + k, new_conf[k])
                del new_conf[k]

            # for the pattern section : { 'key' : 'value' }
            parser = ConfigParser()
            parser.read_dict(new_conf)
            # Password is same for RABBITMQINGRESSPROCESSOR, RABBITMQEGRESSPROCESSOR & LOGGINGPROCESSOR
            rbmq_pass = salt.client.Caller().function('pillar.get',
                            'rabbitmq:sspl:RABBITMQINGRESSPROCESSOR:password')
            for sect in parser.sections():
                for k, v in parser.items(sect):
                    if sect in COMMON_CONFIGS and k not in SSPL_CONFIGS:
                        print("{}/{} considering as common config".format(sect, k))
                    else:
                        if k in salt_uniq_attr_per_node:
                            v = salt.client.Caller().function('grains.get', k)
                            self.consul_conn.kv.put('system_information/cluster_id', v)
                        elif sect in salt_uniq_passwd_per_node and k == 'password':
                            if rbmq_pass:
                                v = rbmq_pass
                    self.consul_conn.kv.put(component + '/' + sect + '/' + k, v)

        except Exception as serror:
            print("Error in connecting salt | consul: {}".format(serror))
            print("Exiting ...")
            sys.exit(os.EX_USAGE)


sc = SaltConfig()
sc.set_config()
sc.sync_sspl_config()

# for dev -> need to insert common config in consul.
# for prod -> provisioner is responsible to insert the common config data into consul
if len(sys.argv) >= 2:
    environment = sys.argv[1]
    product = sys.argv[2]
    if environment == 'DEV':
        sc.insert_dev_common_config(product)
