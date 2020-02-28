"""
 ****************************************************************************
 Filename:          if_data.py
 Description:       Defines the JSON message transmitted by the
                    node message handler. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 Creation Date:     06/17/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import time

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg
from framework.utils import mon_utils

class IFdataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the node message handler
    '''

    MESSAGE_VERSION  = "1.0.0"
    RESOURCE_ID = "0"
    RESOURCE_TYPE = "node:interface:nw"
    SEVERITY = "warning"

    def __init__(self, host_id,
                       local_time,
                       interfaces,
                       site_id,
                       node_id,
                       cluster_id,
                       rack_id,
                       alert_type,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       in_time      = "N/A",
                       expires   = -1):
        super(IFdataMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = in_time
        self._expires           = expires
        self._host_id           = host_id
        self._local_time        = local_time
        self._interfaces        = interfaces
        self._site_id           = site_id
        self._node_id           = node_id
        self._cluster_id        = cluster_id
        self._rack_id           = rack_id
        self.alert_type        = alert_type

        epoch_time = str(int(time.time()))
        alert_id = mon_utils.get_alert_id(epoch_time)
        self._json = {
                       "username": self._username,
                       "expires": self._expires,
                       "description": self.DESCRIPTION,
                       "title": self.TITLE,
                       "signature": self._signature,
                       "time": self._time,
                       "message": {
                          "sspl_ll_msg_header": {
                             "msg_version": self.MESSAGE_VERSION,
                             "schema_version": self.SCHEMA_VERSION,
                             "sspl_version": self.SSPL_VERSION,
                          },
                          "sensor_response_type": {
                             "info": {
                                "event_time": epoch_time,
                                "resource_id": self.RESOURCE_ID,
                                "site_id": self._site_id,
                                "node_id": self._node_id,
                                "cluster_id": self._cluster_id,
                                "rack_id": self._rack_id,
                                "resource_type": self.RESOURCE_TYPE
                             },
                             "specific_info": {
                                "localtime": self._local_time,
                                "interfaces": self._interfaces
                             },
                             "host_id": self._host_id,
                             "alert_type":self.alert_type,
                             "severity": self.SEVERITY,
                             "alert_id": alert_id
                          }
                       }
                    }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)

    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid
