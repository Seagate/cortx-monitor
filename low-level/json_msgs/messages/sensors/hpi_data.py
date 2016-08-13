"""
 ****************************************************************************
 Filename:          hpi_data.py
 Description:       Defines the JSON message transmitted by the
                    HPIMonitor.
 Creation Date:     07/07/2015
 Author:            Andy Kim <jihoon.kim@seagate.com>
                    Alex Cordero <alexander.cordero@seagate.com>

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

class HPIDataMsg(BaseSensorMsg):
    """The JSON message transmitted by the HPIMonitor"""

    SENSOR_RESPONSE_TYPE = "disk_status_hpi"
    MESSAGE_VERSION      = "1.0.0"

    def __init__(self, hostId,
                       deviceId,
                       drawer,
                       location,
                       manufacturer,
                       productName,
                       productVersion,
                       serialNumber,
                       wwn,
                       enclosure,
                       driveNum,
                       disk_installed,
                       disk_powered,
                       username  = "SSPL-LL",
                       signature = "N/A",
                       time      = "N/A",
                       expires   = -1):

        super(HPIDataMsg, self).__init__()

        self._username          = username
        self._signature         = signature
        self._time              = time
        self._expires           = expires
        self._hostId            = hostId
        self._deviceId          = deviceId
        self._drawer            = drawer
        self._location          = location
        self._manufacturer      = manufacturer
        self._productName       = productName
        self._productVersion    = productVersion
        self._serialNumber      = serialNumber
        self._wwn               = wwn
        self._enclosure         = enclosure
        self._driveNum          = driveNum
        self._disk_installed    = disk_installed
        self._disk_powered      = disk_powered

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
                                    "hostId" : self._hostId,
                                    "deviceId" : self._deviceId,
                                    "drawer" : int(self._drawer),
                                    "location" : int(self._location),
                                    "manufacturer" : self._manufacturer,
                                    "productName" : self._productName,
                                    "productVersion" : self._productVersion,
                                    "serialNumber" : self._serialNumber,
                                    "wwn" : self._wwn,
                                    "enclosureSN" : self._enclosure,
                                    "diskNum" : int(self._driveNum),
                                    "diskInstalled" : self._disk_installed,
                                    "diskPowered" : self._disk_powered
                                    }
                                }
                          }
                      }

    def getJson(self):
        """Return a validated JSON object"""
        # Validate the current message
        self.validateMsg(self._json)
        return json.dumps(self._json)

    def getHostId(self):
        return self._hostId

    def getDeviceId(self):
        return self._deviceId

    def getDrawer(self):
        return self._drawer

    def getLocation(self):
        return self._location

    def getManufacturer(self):
        return self._manufacturer

    def getProductName(self):
        return self._productName

    def getProductVersion(self):
        return self._productVersion

    def getSerialNumber(self):
        return self._serialNumber

    def getDriveNum(self):
        return self._driveNum

    def getWWN(self):
        return self._wwn

    def setDiskPowered(self, _powered):
        self._json["message"]["sensor_response_type"][self.SENSOR_RESPONSE_TYPE]["diskPowered"] = _powered

    def setDiskInstalled(self, _installed):
        self._json["message"]["sensor_response_type"][self.SENSOR_RESPONSE_TYPE]["diskInstalled"] = _installed

    def set_uuid(self, _uuid):
        self._json["message"]["sspl_ll_msg_header"]["uuid"] = _uuid