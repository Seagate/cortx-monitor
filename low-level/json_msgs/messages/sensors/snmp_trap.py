"""
 ****************************************************************************
 Filename:          snmp_trap.py
 Description:       Defines the JSON message transmitted by SNMP traps sensor. 
                    There may be a time when we need to maintain state as far 
                    as messages being transmitted.  This may involve aggregation 
                    of multiple messages before transmissions or simply 
                    deferring an acknowledgment to a later point in time.  
                    For this reason, the JSON messages are stored as objects 
                    which can be queued up, etc.
 Creation Date:     03/15/2016
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg

class SNMPtrapMsg(BaseSensorMsg):
    """The JSON message transmitted by the SNMP Traps sensor"""

    SENSOR_RESPONSE_TYPE = "snmp_trap"
    MESSAGE_VERSION      = "1.0.0"

    def __init__(self, trap_data,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(SNMPtrapMsg, self).__init__()

        self._trap_data  = str(trap_data).replace('"', "'")
        self._username   = username
        self._signature  = signature
        self._time       = time
        self._expires    = expires

        self._json = {"title" : self.TITLE,
                      "description" : self.DESCRIPTION,
                      "username" : self._username,
                      "signature" : self._signature,
                      "time" : self._time,
                      "expires" : self._expires,

                      "message" : {
                          "sspl_ll_msg_header": {
                                "schema_version" : self.SCHEMA_VERSION,
                                "sspl_version" : self.SSPL_VERSION,
                                "msg_version" : self.MESSAGE_VERSION
                                },
                          "sensor_response_type": {
                                self.SENSOR_RESPONSE_TYPE: {
                                    "trap_data" : self._trap_data
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""    
        # Validate the current message    
        self._json = self.validateMsg(self._json)       
        return json.dumps(self._json)
