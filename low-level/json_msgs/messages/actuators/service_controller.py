"""
 ****************************************************************************
 Filename:          service_controller.py
 Description:       Defines the JSON message transmitted by the
                    ServiceMsgHandler. There may be a time when we need to
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

class ServiceControllerMsg(BaseActuatorMsg):
    '''
    The JSON message transmitted by the ServiceMsgHandler
    '''

    ACTUATOR_MSG_TYPE = "service_controller"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, service_name,
                       service_response,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(ServiceControllerMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = time
        self._expires           = expires
        self._service_name      = service_name
        self._service_response  = service_response

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
                                    "service_name" : self._service_name,
                                    "service_response" : self._service_response
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)

    def get_service_name(self):
        return self._service_name
    
    def set_service_name(self, service_name):
        self._service_name = service_name

    def get_service_response(self):
        return self._service_response

    def set_service_response(self, service_response):
        self._service_response = service_response

    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid