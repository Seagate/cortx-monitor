"""
 ****************************************************************************
 Filename:          real_stor_actuator_ack_response.py
 Description:       Defines the JSON message transmitted by the
                    RealStorActuatorMsgHandler. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 Creation Date:     11/08/2019
 Author:            Pranav Risbud

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json

from json_msgs.messages.actuators.base_actuators_msg import BaseActuatorMsg

class RealStorActuatorAckMsg(BaseActuatorMsg):
    '''
    The JSON message transmitted by the RealStorActuatorMsgHandler
    '''

    ACTUATOR_MSG_TYPE = "real_stor_ack"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, ack_type,
                       ack_msg,
                       uuid      = "N/A",
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(RealStorActuatorAckMsg, self).__init__()

        self._username      = username
        self._signature     = signature
        self._time          = time
        self._expires       = expires
        self._host_id       = ack_msg.get("host_id")
        self._alert_type    = ack_msg.get("alert_type")
        self._severity      = ack_msg.get("severity")

        info = ack_msg.get("info")
        self._site_id = info.get("site_id")
        self._rack_id = info.get("rack_id")
        self._node_id = info.get("node_id")
        self._cluster_id = info.get("cluster_id")
        self._resource_type = info.get("resource_type")
        self._resource_id = info.get("resource_id")
        self._event_time = info.get("event_time")

        self._specific_info = ack_msg.get("specific_info")

        self._ack_type  = ack_type
        self._ack_msg   = ack_msg
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
                              "severity": self._severity,
                              "info": {
                                  "site_id": self._site_id,
                                  "rack_id": self._rack_id,
                                  "node_id": self._node_id,
                                  "cluster_id": self._cluster_id,
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
        self.validateMsg(self._json)
        return json.dumps(self._json)
