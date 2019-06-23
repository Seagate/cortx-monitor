"""
 ****************************************************************************
 Filename:          realstor_psu_data.py
 Description:       Defines the JSON message transmitted by the
                    RealStorEnclMsgHandler for changes in health of PSUs.
 Creation Date:     08/07/2019
 Author:            Malhar Vora

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation,
 distribution or disclosure of this code, for any reason, not expressly
 authorized is prohibited. All other rights are expressly reserved by
 Seagate Technology, LLC.
 ****************************************************************************
"""

import json

from json_msgs.messages.sensors.base_sensors_msg import BaseSensorMsg


class RealStorPSUDataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the Service Watchdogs
    '''

    SENSOR_RESPONSE_TYPE = "enclosure_psu_alert"
    MESSAGE_VERSION = "1.0.0"

    def __init__(self, alert_type,
                 resource_type,
                 info,
                 extended_info,
                 username="SSPL-LL",
                 signature="N/A",
                 time="N/A",
                 expires=-1):

        super(RealStorPSUDataMsg, self).__init__()

        # Header attributes
        self._username = username
        self._time = time
        self._expires = expires
        self._signature = signature

        self._alert_type = alert_type
        self._resource_type = resource_type

        # info attributes
        self._enclosure_id = info.get("enclosure-id")
        self._serial_number = info.get("serial-number")
        self._description = info.get("description")
        self._revision = info.get("revision")
        self._model = info.get("model")
        self._vendor = info.get("vendor")
        self._mfg_vendor_id = info.get("mfg-vendor-id")
        self._location = info.get("location")
        self._part_number = info.get("part-number")
        self._fru_shortname = info.get("fru-shortname")
        self._mfg_date = info.get("mfg-date")
        self._dc12v = info.get("dc12v")
        self._dc5v = info.get("dc5v")
        self._dc33v = info.get("dc33v")
        self._dc12i = info.get("dc12i")
        self._dc5i = info.get("dc5i")
        self._dctemp = info.get("dctemp")
        self._health = info.get("health")
        self._health_reason = info.get("health-reason")
        self._health_recommendation = info.get("health-recommendation")
        self._status = info.get("status")

        self._extended_info = extended_info

        self._json = {"title": self.TITLE,
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
                          },
                          "sensor_response_type": {
                              self.SENSOR_RESPONSE_TYPE: {
                                  "alertType": self._alert_type,
                                  "resourceType": self._resource_type,
                                  "info": {
                                      "enclosure-id": self._enclosure_id,
                                      "serial-number": self._serial_number,
                                      "description": self._description,
                                      "revision": self._revision,
                                      "model": self._model,
                                      "vendor": self._vendor,
                                      "mfg-vendor-id": self._mfg_vendor_id,
                                      "location": self._location,
                                      "part-number": self._part_number,
                                      "fru-shortname": self._fru_shortname,
                                      "mfg-date": self._mfg_date,
                                      "dc12v": self._dc12v,
                                      "dc5v": self._dc5v,
                                      "dc33v": self._dc33v,
                                      "dc12i": self._dc12i,
                                      "dc5i": self._dc5i,
                                      "dctemp": self._dctemp,
                                      "health": self._health,
                                      "health-reason": self._health_reason,
                                      "health-recommendation":
                                          self._health_recommendation,
                                      "status": self._status
                                  },
                                  "extended_info": self._extended_info
                              }
                          }
                      }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)
