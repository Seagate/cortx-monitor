"""
 ****************************************************************************
 Filename:          base_sensor_msg.py
 Description:       All sensor JSON messages extend this base class
                    containing global constants used throughout  
 Creation Date:     01/31/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import json
from jsonschema import Draft3Validator
from jsonschema import validate

from json_msgs.messages.base_msg import BaseMsg
from json_msgs.schemas import sensors 


class BaseSensorMsg(BaseMsg):
    '''
    The base class for all JSON sensor response messages transmitted by SSPL-LL
    '''

    TITLE               = "SSPL-LL Sensor Response"
    DESCRIPTION         = "Seagate Storage Platform Library - Low Level - Sensor Response"
    JSON_SENSOR_SCHEMA  = "SSPL-LL_Sensor_Response.json"


    def __init__(self):
        """Reads in the json schema for all sensor response messages"""
        super(BaseSensorMsg, self).__init__()

        # Read in the sensor schema for validating messages
        fileName = os.path.join(sensors.__path__[0],
                                self.JSON_SENSOR_SCHEMA)
        with open(fileName, 'r') as f:
            _schema = f.read()

        # Remove tabs and newlines
        self._schema = json.loads(' '.join(_schema.split()))

        # Validate the schema
        Draft3Validator.check_schema(self._schema)

    def validateMsg(self, _jsonMsg):
        """Validate the json message against the schema"""             
        validate(_jsonMsg, self._schema)
        