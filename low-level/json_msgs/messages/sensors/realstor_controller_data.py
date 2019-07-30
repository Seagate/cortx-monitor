"""
 ****************************************************************************
 Filename:          realstor_controller_data.py
 Description:       Defines the JSON message transmitted by the
                    RealStorEnclMsgHandler for changes in health of Controllers.
 Creation Date:     07/17/2019
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


class RealStorControllerDataMsg(BaseSensorMsg):
    '''
    The JSON message transmitted by the Service Watchdogs
    '''

    SENSOR_RESPONSE_TYPE = "enclosure_controller_alert"
    MESSAGE_VERSION = "1.0.0"

    def __init__(self, alert_type,
                 resource_type,
                 info,
                 extended_info,
                 username="SSPL-LL",
                 signature="N/A",
                 time="N/A",
                 expires=-1):

        super(RealStorControllerDataMsg, self).__init__()

        # Header attributes
        self._username = username
        self._time = time
        self._expires = expires
        self._signature = signature

        self._alert_type = alert_type
        self._resource_type = resource_type

        # Already filtered out data in realstor_controller_sensor.py now adding info attributes
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
                                      "controller-id" : self._controller_id,
                                      "serial-number" : self._serial_number,
                                      "hardware-version" : self._hardware_version,
                                      "cpld-version" : self._cpld_version,
                                      "mac-address" : self._mac_address,
                                      "node-wwn" : self._node_wwn,
                                      "ip-address" : self._ip_address,
                                      "ip-subnet-mask" : self._ip_subnet_mask,
                                      "ip-gateway" : self._ip_gateway,
                                      "disks" : self._disks,
                                      "number-of-storage-pools" : self._number_of_storage_pools,
                                      "virtual-disks" : self._virtual_disks,
                                      "host-ports" : self._host_ports,
                                      "drive-channels" : self._drive_channels,
                                      "drive-bus-type" : self._drive_bus_type,
                                      "status" : self._status,
                                      "failed-over" : self._failed_over,
                                      "fail-over-reason" : self._fail_over_reason,
                                      "vendor" : self._vendor,
                                      "model" : self._model,
                                      "platform-type" : self._platform_type,
                                      "write-policy" : self._write_policy,
                                      "description" : self._description,
                                      "part-number" : self._part_number,
                                      "revision" : self._revision,
                                      "mfg-vendor-id" : self._mfg_vendor_id,
                                      "locator-led" : self._locator_led,
                                      "health" : self._health,
                                      "health-reason" : self._health_reason,
                                      "position" : self._position,
                                      "redundancy-mode" : self._redundancy_mode,
                                      "redundancy-status" : self._redundancy_status,
                                      "compact-flash" : self._compact_flash,
                                      "network-parameters" : self._network_parameters,
                                      "expander-ports" : self._expander_ports,
                                      "expanders" : self._expanders,
                                      "port" : self._port
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
