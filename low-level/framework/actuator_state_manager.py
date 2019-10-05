"""
 ****************************************************************************
 Filename:          actuator_state_manager.py
 Description:       Functionality to get/set/query the status of actuators.

 Creation Date:     10/05/2019
 Author:            Malhar Vora

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""


class ActuatorStateManager(object):
    """Maintain a states of various actuators"""

    # States for actuators
    IMPORTED = 0
    INITIALIZING = 1
    INITIALIZED = 2

    def __init__(self):
        self._actuator_state_table = dict()

    def set_state(self, actuator_name, state):
        """Updates the state of <actuator_name>"""
        if not actuator_name or len(actuator_name.strip()) == 0:
            raise TypeError("Actuator name can not be blank")
        if state is None or state not in [0, 1, 2]:
            raise TypeError("Invalid actuator state")
        self._actuator_state_table[actuator_name] = state

    def get_state(self, actuator_name):
        """Returns the state of <actuator_name>"""
        return self._actuator_state_table.get(actuator_name)

    def get_table(self):
        """Returns the internal actuator state table"""
        return self._actuator_state_table

    def is_initialized(self, actuator_name):
        """Returns a True/False according to actuator is initialized"""
        return self.get_state(actuator_name) == ActuatorStateManager.INITIALIZED

    def is_initializing(self, actuator_name):
        """Returns a True/False according to actuator is initializing"""
        return self.get_state(actuator_name) == ActuatorStateManager.INITIALIZING

    def is_imported(self, actuator_name):
        """Returns a True/False according to actuator is imported"""
        return self.get_state(actuator_name) == ActuatorStateManager.IMPORTED


actuator_state_manager = ActuatorStateManager()
