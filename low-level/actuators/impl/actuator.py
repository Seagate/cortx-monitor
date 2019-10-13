"""
Abstract Base class for Actuators
"""

import abc


class Actuator(object):
    """Base class for all the actuator classes
    """
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        """init method"""
        super(Actuator, self).__init__()

    @abc.abstractmethod
    def perform_request():
        """Accepts request and performs actual operation
        """
