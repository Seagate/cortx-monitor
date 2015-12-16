"""
 ****************************************************************************
 Filename:          cpu_data.py
 Description:       Defines the JSON message transmitted by the
                    node message handler. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 Creation Date:     06/12/2015
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

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg

class CPUdataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the node message handler
    '''

    ACTUATOR_MSG_TYPE = "cpu_data"
    MESSAGE_VERSION  = "1.0.0"

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
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(CPUdataMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = time
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


        self._json = {"title" : self.TITLE,
                      "description" : self.DESCRIPTION,
                      "username" : self._username,
                      "signature" : self._signature,
                      "time" : self._time,
                      "expires" : self._expires,

                      "message" : {
                          "sspl_ll_msg_header": {
                              "schema_version" : self.SCHEMA_VERSION,
                              "sspl_version"   : self.SSPL_VERSION,
                              "msg_version"    : self.MESSAGE_VERSION,
                              },
                          "sensor_response_type": {
                              self.ACTUATOR_MSG_TYPE: {
                                  "hostId"        : self._host_id,
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
                                  "coreData"      : self._core_data
                                  }
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
