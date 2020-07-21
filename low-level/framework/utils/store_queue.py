"""
 ****************************************************************************
 Filename:          store_queue.py
 Description:       Queue implementation on top of store
 Creation Date:     03/23/2020
 Author:            Sandeep Anjara

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by
 Seagate Technology, LLC.
 ****************************************************************************
 """

import sys

from framework.utils.store_factory import store
from framework.utils.config_reader import ConfigReader
from framework.utils.service_logging import logger

class StoreQueue:

    RABBITMQPROCESSOR    = 'EGRESSPROCESSOR'
    LIMIT_CONSUL_MEMORY  = 'limit_consul_memory'

    def __init__(self):
        self._conf_reader = ConfigReader()
        self._max_size = int(self._conf_reader._get_value_with_default(self.RABBITMQPROCESSOR,
                                                                self.LIMIT_CONSUL_MEMORY, 50000000))
        self._current_size = store.get("SSPL_MEMORY_USAGE")
        if self._current_size is None:
            store.put(0, "SSPL_MEMORY_USAGE")

        self._head = store.get("SSPL_MESSAGE_HEAD_INDEX")
        if self._head is None:
            store.put(0, "SSPL_MESSAGE_HEAD_INDEX")

        self._tail = store.get("SSPL_MESSAGE_TAIL_INDEX")
        if self._tail is None:
            store.put(0, "SSPL_MESSAGE_TAIL_INDEX")

    @property
    def current_size(self):
        return store.get("SSPL_MEMORY_USAGE")

    @current_size.setter
    def current_size(self, size):
        store.put(size, "SSPL_MEMORY_USAGE")

    @property
    def head(self):
        return store.get("SSPL_MESSAGE_HEAD_INDEX")

    @head.setter
    def head(self, index):
        store.put(index, "SSPL_MESSAGE_HEAD_INDEX")

    @property
    def tail(self):
        return store.get("SSPL_MESSAGE_TAIL_INDEX")

    @tail.setter
    def tail(self, index):
        store.put(index, "SSPL_MESSAGE_TAIL_INDEX")

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
        item = store.get(f"SSPL_UNSENT_MESSAGES/{self.head}")
        store.delete(f"SSPL_UNSENT_MESSAGES/{self.head}")
        self.head += 1
        self.current_size -= sys.getsizeof(item)
        return item

    def put(self, item):
        size_of_item = sys.getsizeof(item)
        if self.is_full(size_of_item):
            logger.debug("StoreQueue, put, consul memory usage exceded limit, \
                removing old message")
            self._create_space(size_of_item)
        store.put(item, f"SSPL_UNSENT_MESSAGES/{self.tail}", pickled=False)
        self.tail += 1
        self.current_size += size_of_item
        logger.debug("StoreQueue, put, current memory usage %s" % self.current_size)

store_queue = StoreQueue()