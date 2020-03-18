"""
 ****************************************************************************
 Filename:          node_hw_data.py
 Description:       Defines the JSON message transmitted by the node_data_msg_handler
                    for changes in FRU and sensors like voltage, temperature.
 Creation Date:     11/04/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2019/04/11 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg

class NodeHWDataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the NodeFruData sensor
    '''

    SENSOR_MSG_TYPE = "node_hw_data"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(NodeHWDataMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = time
        self._expires           = expires

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
                                "msg_version" : self.MESSAGE_VERSION,
                                }
                            }
                        }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)

    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid

class NodeIPMIDataMsg(NodeHWDataMsg):
    def __init__(self, fru):
        super(NodeIPMIDataMsg, self).__init__()

        self.fru = fru
        alert_type = fru.get("alert_type")
        severity = fru.get("severity")
        info = fru.get("info")
        specific_info = fru.get("specific_info")
        host_id = fru.get("host_id")
        alert_id = fru.get("alert_id")

        node_ipmi_data = {"host_id": host_id,
                         "alert_type": alert_type,
                         "alert_id": alert_id,
                         "severity": severity,
                         "info": info,
                         "specific_info": specific_info}

        self._json["message"]["sensor_response_type"] = node_ipmi_data
