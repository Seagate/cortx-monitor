# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Defines the JSON message transmitted by the node_data_msg_handler
                    for changes in RAID. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 ****************************************************************************
"""

import json

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg

class RAIDIntegrityMsg(BaseSensorMsg):

    '''
    The JSON message transmitted by the Service Watchdogs
    '''

    ACTUATOR_MSG_TYPE = "raid_integrity_data"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, host_id,
                       alert_type,
                       alert_id,
                       severity,
                       info,
                       specific_info,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(RAIDIntegrityMsg, self).__init__()

        self._host_id           = host_id
        self._alert_id          = alert_id
        self._alert_type        = alert_type
        self._severity          = severity
        self._sensor_info       = info
        self._sensor_specific_info  = specific_info
        self._username          = username
        self._signature         = signature
        self._time              = time
        self._expires           = expires
        self._site_id = self._sensor_info.get("site_id")
        self._rack_id = self._sensor_info.get("rack_id")
        self._node_id = self._sensor_info.get("node_id")
        self._node_id = self._sensor_info.get("node_id")
        self._cluster_id = self._sensor_info.get("cluster_id")
        self._resource_id = self._sensor_info.get("resource_id")
        self._resource_type = self._sensor_info.get("resource_type")
        self._event_time = self._sensor_info.get("event_time")
        self._error_msg = self._sensor_specific_info.get("error")

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
                                    "host_id" : self._host_id,
                                    "alert_id": self._alert_id,
                                    "alert_type": self._alert_type,
                                    "severity": self._severity,
                                    "info": {
                                            "site_id": self._site_id,
                                            "rack_id": self._rack_id,
                                            "node_id": self._node_id,
                                            "cluster_id": self._cluster_id,
                                            "resource_id": self._resource_id,
                                            "resource_type": self._resource_type,
                                            "event_time": self._event_time,
                                            "description": self._error_msg
                                        },
                                    "specific_info": {
                                            "error": self._error_msg
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)

    def get_host_id(self):
        return self.host_id

    def set_host_id(self, host_id):
        self._host_id = host_id

    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid
