"""
 ****************************************************************************
 Filename:          consulstore.py
 Description:       Utility functions to deal with json data,
                    dump or load from consul
 Creation Date:     01/16/2020
 Author:            Sandeep Anjara <sandeep.anjara@seagate.com>

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2019/06/11 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os
import consul
from common.utils.store import Store
import pickle

class ConsulStore(Store):

    def __init__(self, host, port):
        super(Store, self).__init__()
        self.consul_conn = consul.Consul(host=host, port=port)

    def _get_key(self, key):
        """remove '/' from begining of the key"""

        if key[:1] ==  "/":
            return key[1:]
        else:
            return key

    def put(self, value, key):
        """ write data to given key"""

        try:
            key = self._get_key(key)
            value = pickle.dumps(value)
            self.consul_conn.kv.put(key, value)

        except Exception as gerr:
            print("Error[{0}] while writing data to consul {1}"\
                .format(gerr, key))

    def get(self, key):
        """ Load data from given key"""
        data = None
        try:
            key = self._get_key(key)
            data = self.consul_conn.kv.get(key)[1]
            if data:
                data = data["Value"]
                data = pickle.loads(data)

        except Exception as gerr:
            print("Error{0} while reading data from consul {1}"\
                .format(gerr, key))

        return data
