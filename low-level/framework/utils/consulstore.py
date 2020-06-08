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
from framework.utils.store import Store
from framework.utils.service_logging import logger
import pickle
from framework.base.sspl_constants import MAX_CONSUL_RETRY, WAIT_BEFORE_RETRY
import time
import requests

class ConsulStore(Store):

    def __init__(self, host, port):
        super(Store, self).__init__()
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                self.consul_conn = consul.Consul(host=host, port=port)
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] consul error".format(gerr))
                break

    def _get_key(self, key):
        """remove '/' from begining of the key"""

        if key[:1] ==  "/":
            return key[1:]
        else:
            return key

    def put(self, value, key, pickled=True):
        """ write data to given key"""
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                key = self._get_key(key)
                if pickled:
                    value = pickle.dumps(value)
                self.consul_conn.kv.put(key, value)
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] while writing data to consul {1}" \
                    .format(gerr, key))
                break

    def get(self, key, **kwargs):
        """ Load data from given key"""
        data = None
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                _opt_recurse = kwargs.get("recurse", False)
                key = self._get_key(key)
                data = self.consul_conn.kv.get(key, recurse=_opt_recurse)[1]
                if data:
                    data = data["Value"]
                    try:
                        data = pickle.loads(data)
                    except:
                        pass
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] while reading data from consul {1}" \
                    .format(gerr, key))
                break
        return data

    def exists(self, key):
        """check if key exists
        """
        if self.get(key):
            return True
        else:
            return False

    def delete(self, key):
        """ delete a key
        """
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                key = self._get_key(key)
                self.consul_conn.kv.delete(key)
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] while deleting key from consul {1}" \
                    .format(gerr, key))
                break

    def get_keys_with_prefix(self, prefix):
        """ get keys with given prefix
        """
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                prefix = self._get_key(prefix)
                data = self.consul_conn.kv.get(prefix, recurse=True)[1]
                if data:
                    return [item["Key"][item["Key"].rindex("/")+1:] for item in data]
                else:
                    return []
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] while getting keys with given prefix {1}" \
                    .format(gerr, prefix))
                break
