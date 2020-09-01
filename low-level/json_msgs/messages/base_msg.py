# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       All transmitted JSON messages extend this base class
                    containing global constants used throughout
 ****************************************************************************
"""

import abc

class BaseMsg(metaclass=abc.ABCMeta):
    '''
    The base class for all JSON messages transmitted by SSPL-LL
    '''


    SCHEMA_VERSION  = "1.0.0"
    SSPL_VERSION    = "1.0.0"


    def __init__(self):
        pass

    @abc.abstractmethod
    def getJson(self):
        raise NotImplementedError("Subclasses should implement this!")

    def normalize_kv(self, item):
        """Normalize all keys coming from firmware from - to _"""
        if isinstance(item, dict):
            return {key.replace("-", "_"): self.normalize_kv(value) for key, value in item.items()}
        elif isinstance(item, list):
            return [self.normalize_kv(_) for _ in item]
        elif item == "N/A":
            return "NA"
        else:
            return item
