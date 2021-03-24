# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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
                    Service Monitor. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 ****************************************************************************
"""

import json

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg

class ServiceMonitorMsg(BaseSensorMsg):

    """The JSON message transmitted by the Service Monitor."""

    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, jsonMsg, username  = "SSPL-LL", signature = "N/A",
                       time      = "N/A", expires   = -1):
        """Create message schema for the ServiceMonitor Sensor."""
        super(ServiceMonitorMsg, self).__init__()

        self._username           = username
        self._signature          = signature
        self._time               = time
        self._expires            = expires

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
                          "sensor_response_type": jsonMsg["service_status_alert"]
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)

    def get_service_name(self):
        return self._service_name

    def set_service_name(self, service_name):
        self._service_name = service_name

    def get_service_response(self):
        return self._service_response

    def set_service_response(self, service_response):
        self._service_response = service_response
