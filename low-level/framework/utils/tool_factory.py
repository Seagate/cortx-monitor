"""
Factory module which returns instance of specific tool/utility class.
"""

from framework.utils.sysfs_interface import *
from framework.utils.procfs_interface import *

class ToolFactory(object):
    """"Returns instance of a specific Tool class from the factory"""

    def __init__(self):
        """init method"""
        self._instance = None

    def get_instance(self, utility_name):
        """Returns the instance of the utility by iterating globals
           dictionary"""

        if self._instance is None:
            for key, _ in globals().items():
                if key.lower() == utility_name.lower():
                    self._instance = globals()[key]()
                    break
        return self._instance
