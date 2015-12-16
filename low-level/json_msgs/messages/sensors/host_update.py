"""
 ****************************************************************************
 Filename:          host_update.py
 Description:       Defines the JSON message transmitted by the
                    node message handler. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 Creation Date:     05/20/2015
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

class HostUpdateMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the node message handler
    '''

    ACTUATOR_MSG_TYPE = "host_update"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, host_id,
                       local_time,
                       boot_time,
                       up_time,
                       uname,
                       units,
                       free_mem,
                       total_mem,
                       logged_in_users,
                       process_count,
                       running_process_count,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(HostUpdateMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = time
        self._expires           = expires
        self._host_id           = host_id
        self._local_time        = local_time
        self._boot_time         = boot_time
        self._up_time           = up_time
        self._uname             = uname
        self._free_mem          = free_mem
        self._total_mem         = total_mem
        self._units             = units
        self._logged_in_users   = logged_in_users
        self._process_count     = process_count
        self._running_process_count = running_process_count

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
                                  "hostId"    : self._host_id,
                                  "localtime" : self._local_time,
                                  "bootTime"  : self._boot_time,
                                  "upTime"    : self._up_time,
                                  "uname"     :  self._uname,
                                  "freeMem" : {
                                      "value" : self._free_mem,
                                      "units" : self._units
                                      },
                                  "totalMem" : {
                                      "value" : self._total_mem,
                                      "units" : self._units
                                      },
                                  "loggedInUsers" : self._logged_in_users,
                                  "processCount"  : self._process_count,
                                  "runningProcessCount" : self._running_process_count            
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
