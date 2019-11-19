"""
 ****************************************************************************
 Filename:          realstor_disk_data.py
 Description:       Defines the JSON message transmitted by the
                    RealStor Disk Sensor
 Creation Date:     06/27/2019
 Author:            Chetan Deshmukh <chetan.deshmukh@seagate.com>

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

class RealStorDiskDataMsg(BaseSensorMsg):
    """The JSON message transmitted by the RealStor Disk Sensor"""

    SENSOR_RESPONSE_TYPE = "enclosure_disk_alert"
    MESSAGE_VERSION      = "1.0.0"

    def __init__(self, host_name,
                 alert_type,
                 alert_id,
                 severity,
                 info,
                 specific_info,
                 username="SSPL-LL",
                 signature="N/A",
                 time="N/A",
                 expires=-1):
        super(RealStorDiskDataMsg, self).__init__()

        self._alert_type = alert_type
        self._host_name = host_name
        self._alert_id = alert_id
        self._severity = severity
        self._username = username
        self._signature = signature
        self._time = time
        self._expires = expires

        self._fru_info = info
        self._fru_specific_info = specific_info

        self._site_id = self._fru_info.get("site_id")
        self._rack_id = self._fru_info.get("rack_id")
        self._node_id = self._fru_info.get("node_id")
        self._cluster_id = self._fru_info.get("cluster_id")
        self._resource_id = self._fru_info.get("resource_id")
        self._resource_type = self._fru_info.get("resource_type")
        self._event_time = self._fru_info.get("event_time")

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
                                    "host_id": self._host_name,
                                    "alert_type": self._alert_type,
                                    "alert_id": self._alert_id,
                                    "severity": self._severity,
                                    "info": {
                                            "site_id": self._site_id,
                                            "rack_id": self._rack_id,
                                            "node_id": self._node_id,
                                            "cluster_id": self._cluster_id,
                                            "resource_type": self._resource_type,
                                            "event_time": self._event_time,
                                            "resource_id": self._resource_id
                                        },
                                    "specific_info": self._fru_specific_info
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)
