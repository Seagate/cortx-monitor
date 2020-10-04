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
from framework.utils.filestore import FileStore
from framework.utils.service_logging import logger
import pickle
from framework.base.sspl_constants import MAX_CONSUL_RETRY, WAIT_BEFORE_RETRY
import time
import requests

class ConsulStore(Store):

    def __init__(self, host, port):
        super(Store, self).__init__()
        self._data_sync_required = False
        self._consul_conn_status = False
        self._host = host
        self._port = port
        self._establish_consul_connection(self._host, self._port)
        self._file_store = FileStore()

    def _establish_consul_connection(self, host, port):
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                self.consul_conn = consul.Consul(host=host, port=port)
                self._consul_conn_status = True
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                self._consul_conn_status = False
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] consul error".format(gerr))
                self._consul_conn_status = False
                break

    def _get_key(self, key):
        """remove '/' from begining of the key"""

        if key[:1] ==  "/":
            return key[1:]
        else:
            return key

    def _dump_filestore_to_consulstore(self):
        """Pop entries from the file list and update consul store"""
        # Get a list of modified entries in a filestore
        files = self._file_store.get_keys_with_prefix("/_M")

        for file in files:
            key = os.path.relpath(file, "/_M")
            value = self._file_store.get("/" + key)
            self.consul_conn.kv.put(key, value)

        # Get a list of deleted entries in a filestore
        files = self._file_store.get_keys_with_prefix("/_D")

        for file in files:
            key = os.path.relpath(file, "/_D")
            value = self._file_store.get(key)
            self.consul_conn.kv.delete(key)

        self._data_sync_required = False

    def _add_entry_in_file_list(self, key, value):
        """Prepare list of entries which are added or deleted when consul was down"""
        self._file_store.put(key, value)

    def _consul_store_put(self, key, value, pickled):
        "write data to giver key in consul"
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                consul_key = self._get_key(key)
                if pickled:
                    consul_value = pickle.dumps(value)
                self.consul_conn.kv.put(consul_key, consul_value)
                self._consul_conn_status = True
                break
            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                self._consul_conn_status = False
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] while writing data to consul {1}" \
                    .format(gerr, consul_key))
                self._consul_conn_status = False
                break

    def put(self, value, key, pickled=True):
        """ write data to given key"""
        self._consul_store_put(key, value, pickled)
        self._file_store.put(value, key, pickled)

        if self._consul_conn_status is False:
            self._add_entry_in_file_list(os.path.join("/_M", key), value)
            self._data_sync_required = True

    def _consul_store_get(self, key, kwargs):
        """ Load data from given key from consul"""
        data = None
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                _opt_recurse = kwargs.get("recurse", False)
                consul_key = self._get_key(key)
                data = self.consul_conn.kv.get(consul_key, recurse=_opt_recurse)[1]
                self._consul_conn_status = True
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
                self._consul_conn_status = False
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] while reading data from consul {1}" \
                    .format(gerr, consul_key))
                self._consul_conn_status = False
                break

        return data

    def get(self, key, **kwargs):
        """ Load data from given key"""
        data = None
        if self._consul_conn_status is False:
            self._establish_consul_connection(self._host, self._port)

        if self._consul_conn_status and self._data_sync_required:
            self._dump_filestore_to_consulstore()
        
        data = self._consul_store_get(key, kwargs)

        if self._consul_conn_status is False:
            data = self._file_store.get(key,kwargs)

        return data

    def exists(self, key):
        """check if key exists
        """
        if self.get(key):
            return True
        else:
            return self._file_store.exists(key)

    def _consul_store_delete(self, key):
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                consul_key = self._get_key(key)
                self.consul_conn.kv.delete(consul_key)
                self._consul_conn_status = True
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                self._consul_conn_status = False
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] while deleting key from consul {1}" \
                    .format(gerr, consul_key))
                self._consul_conn_status = False
                break

    def delete(self, key):
        """ delete a key
        """
        self._consul_store_delete(key)
        self._file_store.delete(key)
        if self._consul_conn_status is False:
            self._add_entry_in_file_list(os.path.join("/_D", key), None)
            self._data_sync_required = True

    def _consul_store_get_keys_with_prefix(self, prefix):
        """ get keys with given prefix
        """
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                prefix = self._get_key(prefix)
                data = self.consul_conn.kv.get(prefix, recurse=True)[1]
                self._consul_conn_status = True
                if data:
                    return [item["Key"][item["Key"].rindex("/")+1:] for item in data]
                else:
                    return []
                break

            except requests.exceptions.ConnectionError as connerr:
                logger.warn("Error[{0}] consul connection refused Retry Index {1}" \
                    .format(connerr, retry_index))
                self._consul_conn_status = False
                time.sleep(WAIT_BEFORE_RETRY)

            except Exception as gerr:
                logger.warn("Error[{0}] while getting keys with given prefix {1}" \
                    .format(gerr, prefix))
                self._consul_conn_status = False
                break

    def get_keys_with_prefix(self, prefix):
        """ get keys with given prefix
        """
        files = None
        if self._consul_conn_status is False:
            self._establish_consul_connection(self._host, self._port)

        if self._consul_conn_status and self._data_sync_required:
            self._dump_filestore_to_consulstore()

        files = self._consul_store_get_keys_with_prefix(prefix)

        if self._consul_conn_status is False:
            files = self._file_store.get_keys_with_prefix(prefix)

        return files
