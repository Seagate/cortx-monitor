"""
 ****************************************************************************
 Filename:          service_watchdog.py
 Description:       Defines the JSON message transmitted by the
                    Service Watchdogs. There may be a time when we need to
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

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg

class ServiceWatchdogMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the Service Watchdogs
    '''

    ACTUATOR_MSG_TYPE = "service_watchdog"
    MESSAGE_VERSION  = "1.0.0"

    def __init__(self, service_name,
                       state,
                       previous_state,
                       substate,
                       previous_substate,
                       pid,
                       previous_pid,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):
        super(ServiceWatchdogMsg, self).__init__()

        self._username           = username
        self._signature          = signature
        self._time               = time
        self._expires            = expires
        self._service_name       = service_name
        self._state              = state
        self._previous_state     = previous_state
        self._substate           = substate
        self._previous_substate  = previous_substate
        self._pid                = pid
        self._previous_pid       = previous_pid

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
                                    "service_name" : self._service_name,
                                    "service_state" : self._state,
                                    "previous_service_state" : self._previous_state,
                                    "service_substate": self._substate,
                                    "previous_service_substate": self._previous_substate,
                                    "pid" : self._pid,
                                    "previous_pid" : self._previous_pid
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self._json = self.validateMsg(self._json)
        return json.dumps(self._json)

    def get_service_name(self):
        return self._service_name
    
    def set_service_name(self, service_name):
        self._service_name = service_name

    def get_service_response(self):
        return self._service_response

    def set_service_response(self, service_response):
        self._service_response = service_response
