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
  Description:       Functionality to get/set/query the status of actuators.

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
