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
  Description:       All sensor JSON messages extend this base class
                    containing global constants used throughout
 ****************************************************************************
"""

import os
import json
from jsonschema import Draft3Validator
from jsonschema import validate

from json_msgs.messages.base_msg import BaseMsg
from json_msgs.schemas import sensors
from framework.base.sspl_constants import RESOURCE_PATH

class BaseSensorMsg(BaseMsg):
    '''
    The base class for all JSON sensor response messages transmitted by SSPL-LL
    '''

    TITLE               = "SSPL Sensor Response"
    DESCRIPTION         = "Seagate Storage Platform Library - Sensor Response"
    JSON_SENSOR_SCHEMA  = "SSPL-LL_Sensor_Response.json"


    def __init__(self):
        """Reads in the json schema for all sensor response messages"""
        super(BaseSensorMsg, self).__init__()

        # Read in the sensor schema for validating messages
        #fileName = os.path.join(sensors.__path__[0],
        #                        self.JSON_SENSOR_SCHEMA)
        fileName = os.path.join(RESOURCE_PATH + '/sensors',
                                self.JSON_SENSOR_SCHEMA)
        with open(fileName, 'r') as f:
            _schema = f.read()

        # Remove tabs and newlines
        self._schema = json.loads(' '.join(_schema.split()))

        # Validate the schema
        Draft3Validator.check_schema(self._schema)

    def validateMsg(self, _jsonMsg):
        """Validate the json message against the schema"""
        _jsonMsg = self.normalize_kv(_jsonMsg)
        validate(_jsonMsg, self._schema)
        return _jsonMsg
