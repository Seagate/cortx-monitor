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
import socket
import time

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg
from framework.utils import mon_utils

class IEMDataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the IEMSensor
    '''

    MESSAGE_VERSION = "1.0.0"

    def __init__(self,
                 info,
                 username="SSPL-LL",
                 signature="N/A",
                 expires=-1):

        super(IEMDataMsg, self).__init__()

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
                        "event_time": info.get("event_time"),
                        "resource_id": "iem",
                        "site_id": info.get("site_id"),
                        "node_id": info.get("node_id"),
                        "cluster_id": info.get("cluster_id"),
                        "rack_id": info.get("rack_id"),
                        "resource_type": "iem"
                    },
                    "alert_type": info.get("alert_type"),
                    "severity": info.get("severity"),
                    "specific_info": {
                        "source": info.get("source_id"),
                        "component": info.get("component_id"),
                        "module": info.get("module_id"),
                        "event": info.get("event_id"),
                        "description": info.get("description"),
                        "IEC": info.get("IEC")
                    },
                    "alert_id": mon_utils.get_alert_id(self._epoch_time),
                    "host_id": socket.getfqdn()
                }
            }
        }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)
