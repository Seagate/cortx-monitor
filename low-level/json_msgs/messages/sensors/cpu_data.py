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
                    node message handler. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 ****************************************************************************
"""

import json
import time
from framework.utils.mon_utils import MonUtils
from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg

class CPUdataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the node message handler
    '''

    ACTUATOR_MSG_TYPE = "cpu_data"
    MESSAGE_VERSION  = "1.0.0"

    SEVERITY = "warning"
    RESOURCE_TYPE = "node:os:cpu_usage"
    RESOURCE_ID = "0"

    def __init__(self, host_id,
                       local_time,
                       csps,
                       idle_time,
                       interrupt_time,
                       iowait_time,
                       nice_time,
                       softirq_time,
                       steal_time,
                       system_time,
                       user_time,
                       core_data,
                       cpu_usage,
                       alert_type,
                       event,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       in_time      = "N/A",
                       expires   = -1):
        super(CPUdataMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = in_time
        self._expires           = expires
        self._host_id           = host_id
        self._local_time        = local_time
        self._csps              = csps
        self._idle_time         = idle_time
        self._interrupt_time    = interrupt_time
        self._iowait_time       = iowait_time
        self._nice_time         = nice_time
        self._softirq_time      = softirq_time
        self._steal_time        = steal_time
        self._system_time       = system_time
        self._user_time         = user_time
        self._core_data         = core_data
        self._cpu_usage         = cpu_usage
        self.alert_type         = alert_type
        self.event              = event

        if self.alert_type == "fault_resolved":
            self.SEVERITY = "informational"

        epoch_time = str(int(time.time()))
        alert_id = MonUtils.get_alert_id(epoch_time)

        self._json = {
                      "username" : self._username,
                      "description" : self.DESCRIPTION,
                      "title" : self.TITLE,
                      "expires" : self._expires,
                      "signature" : self._signature,
                      "time" : epoch_time,

                      "message" : {
                          "sspl_ll_msg_header": {
                              "schema_version" : self.SCHEMA_VERSION,
                              "sspl_version"   : self.SSPL_VERSION,
                              "msg_version"    : self.MESSAGE_VERSION,
                              },
                          "sensor_response_type": {
                              "alert_type": self.alert_type,
                              "severity": self.SEVERITY,
                              "alert_id": alert_id,
                              "host_id": self._host_id,
                              "info": {
                                "resource_type": self.RESOURCE_TYPE,
                                "resource_id": self.RESOURCE_ID,
                                "event_time": epoch_time,
                                "description": self.event
                              },
                          "specific_info": {
                                  "localtime"     : self._local_time,
                                  "csps"          : self._csps,
                                  "idleTime"      : self._idle_time,
                                  "interruptTime" : self._interrupt_time,
                                  "iowaitTime"    : self._iowait_time,
                                  "niceTime"      : self._nice_time,
                                  "softirqTime"   : self._softirq_time,
                                  "stealTime"     : self._steal_time,
                                  "systemTime"    : self._system_time,
                                  "userTime"      : self._user_time,
                                  "coreData"      : self._core_data,
                                  "cpu_usage"     : self._cpu_usage
                              }
                          }
                      }
                  }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)

    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid
