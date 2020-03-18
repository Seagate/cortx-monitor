"""
 ****************************************************************************
 Filename:          base_actuator_msg.py
 Description:       All actuator JSON messages extend this base class
                    containing global constants used throughout
 Creation Date:     03/03/2015
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
from json_msgs.schemas import actuators
from framework.base.sspl_constants import RESOURCE_PATH

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
        #fileName = os.path.join(actuators.__path__[0],
        #                        self.JSON_ACTUATOR_SCHEMA)
        with open(fileName, 'r') as f:
            self._schema = json.load(f)

        # Validate the schema
        Draft3Validator.check_schema(self._schema)

    def validateMsg(self, _jsonMsg):
        """Validate the json message against the schema"""
        _jsonMsg = self.normalize_dict_keys(_jsonMsg)
        validate(_jsonMsg, self._schema)
        return _jsonMsg
