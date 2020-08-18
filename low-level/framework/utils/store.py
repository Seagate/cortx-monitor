# Copyright (c) 2019-2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Abstract base class for store implementation
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
