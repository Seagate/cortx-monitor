# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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
  Description:  Defines the JSON message transmitted for any module thread
                failure or recovery.
  ****************************************************************************
"""

import json
import socket
import time

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg
from framework.utils.mon_utils import MonUtils


class ThreadMonitorMsg(BaseSensorMsg):
    """The JSON message transmitted for module failure or recovery."""

    MESSAGE_VERSION = "1.0.0"
    RESOURCE_TYPE = "node:sspl:module"

    def __init__(self, info, username="SSPL-LL", signature="N/A", expires=-1):
        """Initialize thread monitoring message."""
        super(ThreadMonitorMsg, self).__init__()
        self._epoch_time = str(int(time.time()))

        self._json = {
            "username": username,
            "description": self.DESCRIPTION,
            "title": self.TITLE,
            "expires": expires,
            "signature": signature,
            "time": self._epoch_time,
            "message": {
                "sspl_ll_msg_header": {
                    "schema_version": self.SCHEMA_VERSION,
                    "sspl_version": self.SSPL_VERSION,
                    "msg_version": self.MESSAGE_VERSION,
                },
                "sensor_response_type": {
                    "info": {
                        "event_time": self._epoch_time,
                        "resource_id": info.get("module_name"),
                        "resource_type": self.RESOURCE_TYPE,
                        "description": info.get("description"),
                        "impact": info.get("impact"),
                        "recommendation": info.get("recommendation")
                    },
                    "alert_type": info.get("alert_type"),
                    "severity": info.get("severity"),
                    "specific_info": info.get("specific_info"),
                    "alert_id": MonUtils.get_alert_id(self._epoch_time),
                    "host_id": socket.getfqdn()
                }
            }
        }

    def getJson(self):
        """Return a validated JSON object"""
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)
