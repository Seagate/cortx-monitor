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
                    RealStorActuatorMsgHandler. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 ****************************************************************************
"""

import json

from json_msgs.messages.actuators.base_actuators_msg import BaseActuatorMsg

class RealStorActuatorMsg(BaseActuatorMsg):
    '''
    The JSON message transmitted by the RealStorActuatorMsgHandler
    '''

    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, sensor_response,
                       uuid      = "N/A",
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(RealStorActuatorMsg, self).__init__()

        self._username      = username
        self._signature     = signature
        self._time          = time
        self._expires       = expires
        self._host_id       = sensor_response.get("host_id")
        self._alert_type    = sensor_response.get("alert_type")
        self._alert_id      = sensor_response.get("alert_id")
        self._severity      = sensor_response.get("severity")

        info = sensor_response.get("info")
        self._resource_type = info.get("resource_type")
        self._resource_id = info.get("resource_id")
        self._event_time = info.get("event_time")

        self._specific_info = sensor_response.get("specific_info")

        self._uuid      = uuid

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
                              "uuid" : self._uuid
                          },
                          "actuator_response_type": {
                              "host_id": self._host_id,
                              "alert_type": self._alert_type,
                              "alert_id": self._alert_id,
                              "severity": self._severity,
                              "info": {
                                  "resource_type": self._resource_type,
                                  "resource_id": self._resource_id,
                                  "event_time": self._event_time,
                              },
                              "specific_info": self._specific_info
                          }
                      }
                  }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)
