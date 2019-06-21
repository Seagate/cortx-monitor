"""
 ****************************************************************************
 Filename:          realstor_disk_data.py
 Description:       Defines the JSON message transmitted by the
                    RealStor Disk Sensor
 Creation Date:     06/27/2019
 Author:            Chetan Deshmukh <chetan.deshmukh@seagate.com>

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

class RealStorDiskDataMsg(BaseSensorMsg):
    """The JSON message transmitted by the RealStor Disk Sensor"""

    SENSOR_RESPONSE_TYPE = "enclosure_disk_alert"
    MESSAGE_VERSION      = "1.0.0"

    def __init__(self, alertType,
                       resourceType,
                       info,
                       extendedInfo,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):

        super(RealStorDiskDataMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = time
        self._expires           = expires
        self._alertType         = alertType
        self._resourceType      = resourceType
        self._description       = info['description']
        self._slot              = info['slot']
        self._status            = info['status']
        self._architecture      = info['architecture']
        self._interface         = info['interface']
        self._serialNumber      = info['serial-number']
        self._size              = info['size']
        self._vendor            = info['vendor']
        self._model             = info['model']
        self._revision          = info['revision']
        self._temperature       = info['temperature']
        self._LEDStatus         = info['LED-status']
        self._locatorLED        = info['locator-LED']
        self._blinkState        = info['blink']
        self._smart             = info['smart']
        self._health            = info['health']
        self._healthReason      = info['health-reason']
        self._healthRecommendation = info['health-recommendation']
        self._enclosureId       = info['enclosure-id']
        self._enclosureWWN      = info['enclosure-wwn']
        self._enclosureFamily   = info['enclosure-family']
        self._extendedInfo      = extendedInfo

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
                                self.SENSOR_RESPONSE_TYPE: {
                                    "alert_type" : self._alertType,
                                    "resource_type" : self._resourceType,
                                    "info": {
                                        "description" : self._description,
                                        "slot" : self._slot,
                                        "status" : self._status,
                                        "architecture" : self._architecture,
                                        "interface" : self._interface,
                                        "serial-number" : self._serialNumber,
                                        "size" : self._size,
                                        "vendor" : self._vendor,
                                        "model" : self._model,
                                        "revision" : self._revision,
                                        "temperature" : self._temperature,
                                        "LED-status" : self._LEDStatus,
                                        "locator-LED" : self._locatorLED,
                                        "blink-state" : self._blinkState,
                                        "SMART" : self._smart,
                                        "health" : self._health,
                                        "health-reason" : self._healthReason,
                                        "health-recommendation" : self._healthRecommendation,
                                        "enclosure-family" : self._enclosureFamily,
                                        "enclosure-id" : self._enclosureId,
                                        "enclosure-wwn" : self._enclosureWWN
                                     },
                                    "extended_info": self._extendedInfo
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)
