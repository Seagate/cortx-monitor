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
