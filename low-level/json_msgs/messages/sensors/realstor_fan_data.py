"""
 ****************************************************************************
 Filename:          realstor_fan_data.py
 Description:       Defines the JSON message transmitted by the real_stor_encl_msg_handler
                    for changes in FRU.
 Creation Date:     10/07/2019
 Author:            Madhura Mande

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

class RealStorFandataMsg(BaseSensorMsg):

    SENSOR_RESPONSE_TYPE = "enclosure_fan_alert"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, alert_type,
                       resource_type,
                       info,
                       extended_info,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(RealStorFandataMsg, self).__init__()

        self._alert_type = alert_type
        self._resource_type = resource_type
        self._username = username
        self._signature = signature
        self._time = time
        self._expires = expires

        self._name = info.get("name")
        self._description = info.get("description")
        self._part_number = info.get("part-number")
        self._serial_number = info.get("serial-number")
        self._revision = info.get("revision")
        self._mfg_date = info.get("mfg-date")
        self._mfg_vendor_id = info.get("mfg-vendor-id")
        self._fru_location = info.get("fru-location")
        self._fru_status = info.get("fru-status")
        self._enclosure_id = info.get("enclosure-id")

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
                                },
                          "sensor_response_type": {
                                self.SENSOR_RESPONSE_TYPE: {
                                    "alertType": self._alert_type,
                                    "resourceType": self._resource_type,
                                    "info": {
                                        "name": self._name,
                                        "description": self._description,
                                        "part-number": self._part_number,
                                        "serial-number": self._serial_number,
                                        "revision": self._revision,
                                        "mfg-date": self._mfg_date,
                                        "mfg-vendor-id": self._mfg_vendor_id,
                                        "fru-location": self._fru_location,
                                        "fru-status": self._fru_status,
                                        "enclosure-id": self._enclosure_id
                                    },
                                    "extended_info": {
                                        "configuration-serial-number": extended_info
                                    }
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)
