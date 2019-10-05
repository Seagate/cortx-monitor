"""
 ****************************************************************************
 Filename:          ack_response.py
 Description:       Defines the JSON message transmitted by the
                    NodeControllerMsgHandler. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 Creation Date:     07/01/2015
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

from json_msgs.messages.actuators.base_actuators_msg import BaseActuatorMsg

class AckResponseMsg(BaseActuatorMsg):
    '''
    The JSON message transmitted by the NodeControllerMsgHandler
    '''

    ACTUATOR_MSG_TYPE = "ack"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, ack_type,
                       ack_msg,
                       uuid="N/A",
                       username="SSPL-LL",
                       signature="N/A",
                       time="N/A",
                       expires=-1,
                       error_no=0):
        super(AckResponseMsg, self).__init__()

        self._username = username
        self._signature = signature
        self._time = time
        self._expires = expires
        self._ack_type = ack_type
        self._ack_msg = ack_msg
        self._error_no = error_no
        self._uuid = uuid

        self._json = {"title" : self.TITLE,
                      "description": self.DESCRIPTION,
                      "username": self._username,
                      "signature": self._signature,
                      "time": self._time,
                      "expires": self._expires,

                      "message": {
                          "sspl_ll_msg_header": {
                                "schema_version": self.SCHEMA_VERSION,
                                "sspl_version": self.SSPL_VERSION,
                                "msg_version": self.MESSAGE_VERSION,
                                "uuid": self._uuid
                                },
                          "actuator_response_type": {
                                self.ACTUATOR_MSG_TYPE: {
                                    "ack_type": self._ack_type,
                                    "ack_msg": self._ack_msg,
                                    "error_no": self._error_no
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)

    def get_ack_type(self):
        return self._ack_type

    def set_ack_type(self, ack_type):
        self._ack_type = ack_type

    def get_ack_msg(self):
        return self._ack_msg

    def set_ack_msg(self, ack_msg):
        self._ack_msg = ack_msg
