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
from framework.base.sspl_constants import MAX_CONSUL_RETRY, WAIT_BEFORE_RETRY, DATA_PATH
import time
import requests

class ConsulStore(Store):

    def __init__(self, host, port):
        super(Store, self).__init__()
        # Indication of the synchronization if there is a mismatch of the stored data between file store and consul store
        self._data_sync_required = False
        #Indicates whether consul connection is up/down
        self._consul_conn_status = False
        self._consul_host = host
        self._consul_port = port
        self._establish_consul_connection(self._consul_host, self._consul_port)
        self._file_store = FileStore()
        #List of the files which are affected when consul was down
        self._affected_files_list_path = os.path.join(DATA_PATH, "affected_files_list")

    def _establish_consul_connection(self, consul_host, consul_port):
        for retry_index in range(0, MAX_CONSUL_RETRY):
            try:
                self.consul_conn = consul.Consul(consul_host, consul_port)
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

    def _dump_filestore_to_consulstore(self, path):
        """Pop entries from the file list and update consul store."""
        # Get a list of modified entries which are not present in consulstore
        key_list = self._file_store.get(path)

        for key in key_list:
            #get prefix of the key
            action = key.split("/")

            if action[1] == "_M":
                actual_key = os.path.relpath(key, "/_M")
                value = self._file_store.get("/" + actual_key)
                self.consul_conn.kv.put(actual_key, value)

            elif action[1] == "_D":
                actual_key = os.path.relpath(key, "/_D")
                value = self._file_store.get(actual_key)
                self.consul_conn.kv.delete(actual_key)

        self._file_store.delete(path)
        self._data_sync_required = False

    def _update_file_list(self, path, entry):
        """Prepare list of entries which are added or deleted when consul was down."""
        if self._file_store.exists(path):
            key_list = self._file_store.get(path)
            key_list.append(entry)
            self._file_store.put(key_list, path)
        else:
            key_list = [f"{entry}"]
            self._file_store.put(key_list, path)

    def _consul_store_put(self, key, value, pickled):
        """Write data to giver key in consul."""
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

        if self._consul_conn_status is False:
            logger.warn("Consul conn is down: key {0} value {1}".format(key, value))
            file_entry = os.path.join("/_M", key)
            self._update_file_list(self._affected_files_list_path, file_entry)
            self._data_sync_required = True

    def put(self, value, key, pickled=True):
        """Write data to given key."""
        self._consul_store_put(key, value, pickled)
        # Needs back of the stored data in the consul.
        # There is an issue when consul is down as sspl's alerts are dependent on the consul.So, writing data
        # in filestore along with consulstore. It would be getting used when consul connection is down
        self._file_store.put(value, key, pickled)

    def _consul_store_get(self, key, kwargs):
        """Load data from given key from consul."""
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
        """Load data from given key."""
        data = None

        # Try to restores consul connection in case it went down
        if self._consul_conn_status is False:
            self._establish_consul_connection(self._consul_host, self._consul_port)

        if self._consul_conn_status:
            if self._data_sync_required:
                # Dump data from the file store to consul store once the consul connection is restored.
                # TODO: Need to make this asynchronous task, trigger can happen here but current get() should not get delayed
                self._dump_filestore_to_consulstore(self._affected_files_list)
            # Get data from the consul store
            data = self._consul_store_get(key, kwargs)
        else:
            # Consul connetion is down. So, get data from the file store
            logger.warn("Consul conn is down, filestore is being used to get data: key {0}".format(key))
            data = self._file_store.get(key,kwargs)

        return data

    def exists(self, key):
        """Check if key exists."""
        if self.get(key):
            return True
        else:
            return self._file_store.exists(key)

    def _consul_store_delete(self, key):
        """Delete a key from consul store."""
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

        if self._consul_conn_status is False:
            file_entry = os.path.join("/_D", key)
            self._update_file_list(self._affected_files_list_path, file_entry)
            self._data_sync_required = True

    def delete(self, key):
        """Delete a key."""
        self._consul_store_delete(key)
        # Needs back of the stored data in the consul.
        # There is an issue when consul is down as sspl's alerts are dependent on the consul. So, deleting data
        # from the filestore along with consulstore.
        self._file_store.delete(key)

    def _consul_store_get_keys_with_prefix(self, prefix):
        """Get keys with given prefix from consulstore."""
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
        """Get keys with given prefix."""
        files = None

        # Try to restore consul connection in case it went down
        if self._consul_conn_status is False:
            self._establish_consul_connection(self._consul_host, self._consul_port)

        if self._consul_conn_status:
            if self._data_sync_required:
                # Dump data from the file store to consul store once the consul connection is restored.
                # TODO: Need to make this asynchronous task, trigger can happen here but current get() should not get delayed
                self._dump_filestore_to_consulstore(self._affected_files_list_path)
            # Get data from the consul store
            files = self._consul_store_get_keys_with_prefix(prefix)
        else:
            # Consul connetion is down. So, get data from the file store
            files = self._file_store.get_keys_with_prefix(prefix)

        return files
