"""
 ****************************************************************************
 Filename:          iem_data.py
 Description:       Defines the JSON message transmitted by the
                    IEMSensor. Contains IEM related data.
 Creation Date:     08/07/2019
 Author:            Malhar Vora

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation,
 distribution or disclosure of this code, for any reason, not expressly
 authorized is prohibited. All other rights are expressly reserved by
 Seagate Technology, LLC.
 ****************************************************************************
"""

import json

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg


class IEMDataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the IEMSensor
    '''

    SENSOR_RESPONSE_TYPE = "iem_alert"
    MESSAGE_VERSION = "1.0.0"

    def __init__(self,
                 info,
                 username="SSPL-LL",
                 signature="N/A",
                 time="N/A",
                 expires=-1):

        super(IEMDataMsg, self).__init__()

        # Header attributes
        self._username = username
        self._time = time
        self._expires = expires
        self._signature = signature

        self._site_id = info.get("site_id")
        self._node_id = info.get("node_id")
        self._rack_id = info.get("rack_id")
        self._source_id = info.get("source_id")
        self._component_id = info.get("component_id")
        self._module_id = info.get("module_id")
        self._event_id = info.get("event_id")
        self._severity = info.get("severity")
        self._description = info.get("description")

        self._json = {
            "title": self.TITLE,
            "description": self.DESCRIPTION,
            "username": self._username,
            "signature": self._signature,
            "time": self._time,
            "expires": self._expires,

            "message": {
                "sspl_ll_msg_header": {
                    "schema_version": self.SCHEMA_VERSION,
                    "sspl_version": self.SSPL_VERSION,
                    "msg_version": self.MESSAGE_VERSION,
                },
                "sensor_response_type": {
                    self.SENSOR_RESPONSE_TYPE: {
                        "site_id": self._site_id,
                        "rack_id": self._rack_id,
                        "node_id": self._node_id,
                        "source_id": self._source_id,
                        "component_id": self._component_id,
                        "module_id": self._module_id,
                        "event_id": self._event_id,
                        "severity": self._severity,
                        "description": self._description,
                    }
                }
            }
        }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)
