"""
 ****************************************************************************
 Filename:          realstor_fan_data.py
 Description:       Defines the JSON message transmitted by the
                    real_stor_encl_msg_handler for changes in FRU.
 Creation Date:     10/07/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology,
 LLC.
 ****************************************************************************
"""

import json

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg


class RealStorFanDataMsg(BaseSensorMsg):

    SENSOR_RESPONSE_TYPE = "enclosure_fan_module_alert"
    MESSAGE_VERSION = "1.0.0"

    def __init__(self, alert_type,
                 resource_type,
                 info,
                 extended_info,
                 username="SSPL-LL",
                 signature="N/A",
                 time="N/A",
                 expires=-1):
        super(RealStorFanDataMsg, self).__init__()

        self._alert_type = alert_type
        self._resource_type = resource_type
        self._username = username
        self._signature = signature
        self._time = time
        self._expires = expires

        self._fan_module_info = info.get("fan_module")
        self._fan_module_extended_info = extended_info.get("fan_module")

        self._name = self._fan_module_info.get("name")
        self._status = self._fan_module_info.get("status")
        self._location = self._fan_module_info.get("location")
        self._enclosure_id = self._fan_module_info.get("enclosure-id")
        self._health = self._fan_module_info.get("health")
        self._health_reason = self._fan_module_info.get("health-reason")
        self._health_recommendation = \
            self._fan_module_info.get("health-recommendation")
        self._fans = self._fan_module_info.get("fans", [])

        self._position = self._fan_module_extended_info.get("position")
        self._durable_id = self._fan_module_extended_info.get("durable-id")

        self._json = {"title": self.TITLE,
                      "description": self.DESCRIPTION,
                      "username": self._username,
                      "signature": self._signature,
                      "time": self._time,
                      "expires": self._expires,

                      "message": {
                          "sspl_ll_msg_header": {
                                "schema_version": self.SCHEMA_VERSION,
                                "sspl_version": self.SSPL_VERSION,
                                "msg_version": self.MESSAGE_VERSION
                                },
                          "sensor_response_type": {
                                self.SENSOR_RESPONSE_TYPE: {
                                    "alert_type": self._alert_type,
                                    "resource_type": self._resource_type,
                                    "info": {
                                        "fan_module": {
                                            "name": self._name,
                                            "status": self._status,
                                            "location": self._location,
                                            "health": self._health,
                                            "health-reason":
                                                self._health_reason,
                                            "health-recommendation":
                                                self._health_recommendation,
                                            "enclosure-id": self._enclosure_id,
                                            "fans": self._fans
                                        }},
                                    "extended_info": {
                                        "fan_module": {
                                            "position": self._position,
                                            "durable-id": self._durable_id
                                        }}
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)
