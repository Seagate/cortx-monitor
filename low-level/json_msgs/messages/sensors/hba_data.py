# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import json
import time

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg
from framework.utils.mon_utils import MonUtils


class HBADataMsg(BaseSensorMsg):
    """The JSON message transmitted by the node message handler."""

    MESSAGE_VERSION      = "1.0.0"

    def __init__(self, host_name, alert_type, alert_id, severity,
            info={}, specific_info={}, username="SSPL-LL", signature="N/A",
            time="N/A", expires=-1):
        """Initialize HBA data message."""

        super(HBADataMsg, self).__init__()

        self._json = {
            "title": self.TITLE,
            "description": self.DESCRIPTION,
            "username": username,
            "signature": signature,
            "time": time,
            "expires": expires,
            "message": {
            "sspl_ll_msg_header": {
                    "schema_version": self.SCHEMA_VERSION,
                    "sspl_version": self.SSPL_VERSION,
                    "msg_version": self.MESSAGE_VERSION
                    },
            "sensor_response_type": {
                    "host_id": host_name,
                    "alert_type": alert_type,
                    "alert_id": alert_id,
                    "severity": severity,
                    "info": info,
                    "specific_info": specific_info
                }
            }
        }

    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid

    def getJson(self):
        """Return a validated JSON object"""
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)
