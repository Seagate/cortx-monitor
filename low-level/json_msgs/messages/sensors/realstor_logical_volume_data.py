"""
 ****************************************************************************
 Filename:          realstor_logical_volume_data.py
 Description:       Defines the JSON message transmitted by the
                    RealStorEnclMsgHandler for changes in health of Logical
                    Volumes.
 Creation Date:     09/09/2019
 Author:            Satish Darade

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


class RealStorLogicalVolumeDataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the Service Watchdogs
    '''

    SENSOR_RESPONSE_TYPE = "enclosure_logical_volume_alert"
    MESSAGE_VERSION = "1.0.0"

    def __init__(self, alert_type,
                 resource_type,
                 info,
                 extended_info,
                 username="SSPL-LL",
                 signature="N/A",
                 time="N/A",
                 expires=-1):

        super(RealStorLogicalVolumeDataMsg, self).__init__()

        # Header attributes
        self._username = username
        self._time = time
        self._expires = expires
        self._signature = signature

        self._alert_type = alert_type
        self._resource_type = resource_type

        # Already filtered out data in realstor_logical_volume_sensor.py
        # Generic info attributes
        for key, value in info.iteritems():
            setattr(self, '_'+key.replace('.', '_').replace('-','_'), value)

        # extended info attributes
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
                                  "alert_type": self._alert_type,
                                  "resource_type": self._resource_type,
                                  "info": {
                                      "object-name" : self._object_name,
                                      "virtual-disk-name" : self._virtual_disk_name,
                                      "storage-pool-name" : self._storage_pool_name,
                                      "volume-name" : self._volume_name,
                                      "size" : self._size,
                                      "total-size" : self._total_size,
                                      "allocated-size" : self._allocated_size,
                                      "storage-type" : self._storage_type,
                                      "owner" : self._owner,
                                      "serial-number" : self._serial_number,
                                      "write-policy" : self._write_policy,
                                      "volume-type" : self._volume_type,
                                      "volume-class" : self._volume_class,
                                      "blocksize" : self._blocksize,
                                      "blocks" : self._blocks,
                                      "capabilities" : self._capabilities,
                                      "virtual-disk-serial" : self._virtual_disk_serial,
                                      "volume-description" : self._volume_description,
                                      "wwn" : self._wwn,
                                      "progress" : self._progress,
                                      "raidtype" : self._raidtype,
                                      "health" : self._health,
                                      "health-reason" : self._health_reason,
                                      "health-recommendation" : self._health_recommendation,
                                      "disk-group" : self._disk_group
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
