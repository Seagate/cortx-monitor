"""
 ****************************************************************************
 Filename:          raid_data.py
 Description:       Defines the JSON message transmitted by the node_data_msg_handler
                    for changes in RAID. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 Creation Date:     07/17/2015
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

class RAIDdataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the Service Watchdogs
    '''

    ACTUATOR_MSG_TYPE = "raid_data"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, host_id,
                       mdstat,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(RAIDdataMsg, self).__init__()

        self._host_id           = host_id
        self._mdstat            = mdstat
        self._username          = username
        self._signature         = signature
        self._time              = time
        self._expires           = expires

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
                                self.ACTUATOR_MSG_TYPE: {
                                    "hostId" : self._host_id,
                                    "mdstat" : self._mdstat
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)

    def get_host_id(self):
        return self.host_id
    
    def set_host_ide(self, host_id):
        self._host_id = host_id

    def get_mdstat(self):
        return self._mdstat

    def set_mdstat(self, mdstat):
        self._mdstat = mdstat

    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid