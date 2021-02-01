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
  Description:       All actuator JSON messages extend this base class
                    containing global constants used throughout
 ****************************************************************************
"""

import os
import json
from jsonschema import Draft3Validator
from jsonschema import validate

from cortx.sspl.json_msgs.messages.base_msg import BaseMsg
from cortx.sspl.json_msgs.schemas import actuators
from cortx.sspl.framework.base.sspl_constants import RESOURCE_PATH

class BaseActuatorMsg(BaseMsg):
    '''
    The base class for all JSON actuator response messages transmitted by SSPL-LL
    '''

    TITLE                = "SSPL Actuator Response"
    DESCRIPTION          = "Seagate Storage Platform Library - Actuator Response"
    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Response.json"


    def __init__(self):
        """Reads in the json schema for all actuator response messages"""
        super(BaseActuatorMsg, self).__init__()

        # Read in the schema for validating messages
        fileName = os.path.join(RESOURCE_PATH + '/actuators',
                                self.JSON_ACTUATOR_SCHEMA)
        with open(fileName, 'r') as f:
            self._schema = json.load(f)

        # Validate the schema
        Draft3Validator.check_schema(self._schema)

    def validateMsg(self, _jsonMsg):
        """Validate the json message against the schema"""
        _jsonMsg = self.normalize_kv(_jsonMsg)
        validate(_jsonMsg, self._schema)
        return _jsonMsg
