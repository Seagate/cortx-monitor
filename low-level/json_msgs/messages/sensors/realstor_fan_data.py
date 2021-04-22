# Copyright (c) 2019-2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Defines the JSON message transmitted by the
                    real_stor_encl_msg_handler for changes in FRU.
  ****************************************************************************
"""

import json

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg


class RealStorFanDataMsg(BaseSensorMsg):

    SENSOR_RESPONSE_TYPE = "enclosure_fan_module_alert"
    MESSAGE_VERSION = "1.0.0"

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
        super(RealStorFanDataMsg, self).__init__()

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

        self._resource_id = self._fru_info.get("resource_id")
        self._resource_type = self._fru_info.get("resource_type")
        self._event_time = self._fru_info.get("event_time")
        description = self._fru_specific_info.get("health-reason")

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
                                            "resource_type": self._resource_type,
                                            "event_time": self._event_time,
                                            "resource_id": self._resource_id,
                                            "description": description
                                        },
                                    "specific_info": self._fru_specific_info
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)
