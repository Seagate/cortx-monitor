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
from sspl_constants import component, salt_provisioner_pillar_sls, CONSUL_HOST, CONSUL_PORT


class SaltConfig(object):

   @staticmethod
   def set_config():
      try:
         new_conf = salt.client.Caller().function('pillar.get', salt_provisioner_pillar_sls)
         consul_data = new_conf.get('DATASTORE')
         if consul_data and consul_data.get('consul_host'):
            host = consul_data['consul_host']
            port = consul_data['consul_port']
         else:
            host = os.getenv('CONSUL_HOST', CONSUL_HOST)
            port = os.getenv('CONSUL_PORT', CONSUL_PORT)
         consul_conn = consul.Consul(host=host, port=port)

         # for the pattern key : 'value'
         str_keys = [k for k,v in new_conf.items() if isinstance(v, str)]
         for k in str_keys:
               consul_conn.kv.put(component + '/' + k, new_conf[k])
               del new_conf[k]

         # for the pattern section : { 'key' : 'value' }
         parser = ConfigParser()
         parser.read_dict(new_conf)
         for sect in parser.sections():
            for k, v in parser.items(sect):
                  consul_conn.kv.put(component + '/' + sect + '/' + k, v)

      except Exception as serror:
            print("Error in connecting salt | consul: {}".format(serror))
            print("Exiting ...")
            sys.exit(os.EX_USAGE)

SaltConfig.set_config()