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

"""
 ****************************************************************************
  Description:       Utility functions to deal with json data,
                    dump or load from consul
 ****************************************************************************
"""
import os
import consul
from framework.utils.store import Store
from framework.utils.service_logging import logger
import pickle
from framework.base.sspl_constants import MAX_CONSUL_RETRY, WAIT_BEFORE_RETRY, CONSUL_ERR_STRING
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
                consuerr = str(gerr)
                if CONSUL_ERR_STRING == consuerr:
                    logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                        .format(gerr, retry_index))
                    time.sleep(WAIT_BEFORE_RETRY)
                else:
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
        key = self._get_key(key)
        if pickled:
            value = pickle.dumps(value)

        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                self.consul_conn.kv.put(key, value)
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                consulerr = str(gerr)
                if CONSUL_ERR_STRING == consulerr:
                    logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                        .format(gerr, retry_index))
                    time.sleep(WAIT_BEFORE_RETRY)
                else:
                    logger.warn("Error[{0}] while writing data to consul {1}" \
                        .format(gerr, key))
                    break

    def _consul_get(self, key, **kwargs):
        """Load consul data from the given key."""
        data = None
        status = "Failure"

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
                status = "Success"
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                consulerr = str(gerr)
                if CONSUL_ERR_STRING == consulerr:
                    logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                        .format(gerr, retry_index))
                    time.sleep(WAIT_BEFORE_RETRY)
                else:
                    logger.warn("Error[{0}] while reading data from consul {1}" \
                        .format(gerr, key))
                    break

        return data, status

    def get(self, key, **kwargs):
        """ Load data from given key"""
        data, _ = self._consul_get(key, **kwargs)
        return data

    def exists(self, key):
        """check if key exists
        """
        key_present = False
        data, status = self._consul_get(key)

        if data is not None:
            key_present = True

        return key_present, status

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
                consulerr = str(gerr)
                if CONSUL_ERR_STRING == consulerr:
                    logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                        .format(gerr, retry_index))
                    time.sleep(WAIT_BEFORE_RETRY)
                else:
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
                consulerr = str(gerr)
                if CONSUL_ERR_STRING == consulerr:
                    logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                        .format(gerr, retry_index))
                    time.sleep(WAIT_BEFORE_RETRY)
                else:
                    logger.warn("Error[{0}] while getting keys with given prefix {1}" \
                        .format(gerr, prefix))
                    break
