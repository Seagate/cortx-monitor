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
Abstract Base class for all the IPMI implementation
"""

import abc


class IPMI(object):
    """Base class for all IPMI implementation classes
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """Init method"""
        super(IPMI, self).__init__()

    @abc.abstractmethod
    def get_sensor_list_by_entity(self, entity_id):
        """Returns the sensor list based on entity id using IPMI
        """
        raise NotImplementedError("sub class should implement this")

    @abc.abstractmethod
    def get_sensor_list_by_type(self, fru_type):
        """Returns the sensor list based on FRU type using IPMI
        """
        raise NotImplementedError("sub class should implement this")

    @abc.abstractmethod
    def get_sensor_sdr_props(self, sensor_id):
        """Returns sensor software data record based on sensor id
           using IPMI
        """
        raise NotImplementedError("sub class should implement this")

    @abc.abstractmethod
    def get_sensor_props(self):
        """Returns individual sensor instance properties based on
           sensor id using IPMI
        """
        raise NotImplementedError("sub class should implement this")
