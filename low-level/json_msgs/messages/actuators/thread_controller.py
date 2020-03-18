"""
 ****************************************************************************
 Filename:          thread_controller.py
 Description:       Defines the JSON message transmitted by the
                    ThreadController. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 Creation Date:     03/03/2015
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

class ThreadControllerMsg(BaseActuatorMsg):
    '''
    The JSON message transmitted by the Thread Controller
    '''

    ACTUATOR_MSG_TYPE = "thread_controller"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, module_name,
                       thread_response,
                       ack_type  = "N/A",
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(ThreadControllerMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = time
        self._expires           = expires
        self._module_name       = module_name
        self._thread_response   = thread_response

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
                          "actuator_response_type": {
                                self.ACTUATOR_MSG_TYPE: {
                                    "module_name" : self._module_name,
                                    "thread_response" : self._thread_response,
                                    "ack_type" : ack_type
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)

    def get_module_name(self):
        return self._module_name

    def set_module_name(self, module_name):
        self._module_name = module_name

    def get_thread_response(self):
        return self._thread_response

    def set_thread_response(self, thread_response):
        self._thread_response = thread_response
        
    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid
