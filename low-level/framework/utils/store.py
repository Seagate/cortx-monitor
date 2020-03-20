"""
 ****************************************************************************
 Filename:          store.py
 Description:       Abstract base class for store implementation
 Creation Date:     07/26/2019
 Author:            Chetan Deshmukh <chetan.deshmukh@seagate.com>

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2019/06/11 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import abc

class Store(object):
    """Base class for all store implementation classes
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """Init method
        """
        super(Store, self).__init__()

    @abc.abstractmethod
    def put(self, value, key, pickled=True):
        """Write data to store
        """
        raise NotImplementedError("sub class should implement this")

    @abc.abstractmethod
    def get(self, key):
        """get data from store
        """
        raise NotImplementedError("sub class should implement this")

    @abc.abstractmethod
    def exists(self, key):
        """check if key exists
        """
        raise NotImplementedError("sub class should implement this")

    @abc.abstractmethod
    def delete(self, key):
        """ delete data for given key
        """
        raise NotImplementedError("sub class should implement this")

    @abc.abstractmethod
    def get_keys_with_prefix(self, prefix):
        """ get keys with given prefix
        """
        raise NotImplementedError("sub class should implement this")
