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
  Description:       Queue implementation on top of store
  ****************************************************************************
 """

import os
import sys
from framework.base.sspl_constants import DATA_PATH
from framework.utils.store_factory import store
from framework.utils.config_reader import ConfigReader
from framework.utils.service_logging import logger

class StoreQueue:

    RABBITMQPROCESSOR    = 'RABBITMQEGRESSPROCESSOR'
    LIMIT_CONSUL_MEMORY  = 'limit_consul_memory'
    CACHE_DIR_NAME       = "SSPL_UNSENT_MESSAGES"

    def __init__(self):
        self._conf_reader = ConfigReader()
        self._max_size = int(self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                self.LIMIT_CONSUL_MEMORY, 50000000))

        self.cache_dir_path = os.path.join(DATA_PATH, self.CACHE_DIR_NAME)
        self.SSPL_MEMORY_USAGE = os.path.join(self.cache_dir_path, 'SSPL_MEMORY_USAGE')
        self._current_size = store.get(self.SSPL_MEMORY_USAGE)
        if self._current_size is None:
            store.put(0, self.SSPL_MEMORY_USAGE)

        self.SSPL_MESSAGE_HEAD_INDEX = os.path.join(self.cache_dir_path, 'SSPL_MESSAGE_HEAD_INDEX')
        self._head = store.get(self.SSPL_MESSAGE_HEAD_INDEX)
        if self._head is None:
            store.put(0, self.SSPL_MESSAGE_HEAD_INDEX)

        self.SSPL_MESSAGE_TAIL_INDEX = os.path.join(self.cache_dir_path, 'SSPL_MESSAGE_TAIL_INDEX')
        self._tail = store.get(self.SSPL_MESSAGE_TAIL_INDEX)
        if self._tail is None:
            store.put(0, self.SSPL_MESSAGE_TAIL_INDEX)
        self.SSPL_UNSENT_MESSAGES = os.path.join(self.cache_dir_path, 'MESSAGES')

    @property
    def current_size(self):
        return store.get(self.SSPL_MEMORY_USAGE)

    @current_size.setter
    def current_size(self, size):
        store.put(size, self.SSPL_MEMORY_USAGE)

    @property
    def head(self):
        return store.get(self.SSPL_MESSAGE_HEAD_INDEX)

    @head.setter
    def head(self, index):
        store.put(index, self.SSPL_MESSAGE_HEAD_INDEX)

    @property
    def tail(self):
        return store.get(self.SSPL_MESSAGE_TAIL_INDEX)

    @tail.setter
    def tail(self, index):
        store.put(index, self.SSPL_MESSAGE_TAIL_INDEX)

    def is_empty(self):
        if self.tail == self.head:
            self.head = 0
            self.tail = 0
            self.current_size = 0
            return True
        else:
            return False

    def is_full(self, size_of_item):
        return (self.current_size + size_of_item) >= self._max_size

    def _create_space(self, size_of_item, reclaimed_space=0):
        if (self.current_size - reclaimed_space + size_of_item) >= self._max_size:
            reclaimed_space += sys.getsizeof(self.get())
            self._create_space(size_of_item, reclaimed_space)
        else:
            return

    def get(self):
        if self.is_empty():
            return
        item = store.get(f"{self.SSPL_UNSENT_MESSAGES}/{self.head}")
        store.delete(f"{self.SSPL_UNSENT_MESSAGES}/{self.head}")
        self.head += 1
        self.current_size -= sys.getsizeof(item)
        return item

    def put(self, item):
        size_of_item = sys.getsizeof(item)
        if self.is_full(size_of_item):
            logger.debug("StoreQueue, put, consul memory usage exceded limit, \
                removing old message")
            self._create_space(size_of_item)
        store.put(item, f"{self.SSPL_UNSENT_MESSAGES}/{self.tail}", pickled=False)
        self.tail += 1
        self.current_size += size_of_item
        logger.debug("StoreQueue, put, current memory usage %s" % self.current_size)

store_queue = StoreQueue()
