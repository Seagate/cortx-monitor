"""
 ****************************************************************************
 Filename:          node_hw.py
 Description:       Handles messages for Node server requests
 Creation Date:     10/10/2019
 Author:            Satish Darade

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology,
 LLC.
 ****************************************************************************
"""
import abc
import subprocess
import calendar
import time
import socket

from actuators.impl.actuator import Actuator
from framework.base.debug import Debug
from framework.utils.service_logging import logger


class NodeHWactuator(Actuator, Debug):
    """Handles request messages for Node server requests
    """

    ACTUATOR_NAME = "NodeHWactuator"
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "site_id"
    RACK_ID = "rack_id"
    NODE_ID = "node_id"
    NODE_REQUEST_MAP = {
        "disk" : "Drive Slot / Bay",
        "fan" : "Fan",
        "psu" : "Power Supply"
    }

    @staticmethod
    def name():
        """ @return: name of the module."""
        return NodeHWactuator.ACTUATOR_NAME

    def __init__(self, executer, conf_reader):
        super(NodeHWactuator, self).__init__()
        self._site_id = int(conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.SITE_ID,
                                                0))
        self._rack_id = int(conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.RACK_ID,
                                                0))
        self._node_id = int(conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.NODE_ID,
                                                0))
        self.sensor_id_map = None
        self._executer = executer

    def initialize(self):
        """Performs basic Node HW actuator initialization"""

        sensor_id_map = self._executer.get_fru_list_by_type(
            ['fan', 'power supply', 'drive slot / bay'],
            sensor_id_map={})
        self.sensor_id_map = sensor_id_map

    def perform_request(self, json_msg):
        """Performs the Node server request

        @return: The response string from performing the request
        """
        response = ""
        node_request = json_msg.get("node_controller")
        if node_request.get("node_request").split(":")[:3] == ['NDHW', 'node', 'fru']:
            response = self._get_node_fru_info(node_request)
        else:
            pass

        return response

    def _get_node_fru_info(self, node_request):
        """Get the fru information based on node_request
        @return: The response string from performing the request
        """
        response = ""
        self.fru_node_request = node_request.get("node_request").split(":")[3]
        fru = self.NODE_REQUEST_MAP.get(self.fru_node_request)
        fru_instance = node_request.get("resource")

        if fru_instance.isdigit() and isinstance(int(fru_instance), int):
            fru_dict = self.sensor_id_map.get(fru.lower())
            sensor_id = fru_dict[int(fru_instance)]
            common, specific = self._executer.get_sensor_props(sensor_id)
            response = self._create_node_fru_json_message(specific)
            response['instance_id'] = fru_instance
            response['info']['resource_id'] = sensor_id

            # Converting Fru ID From "HDD 0 Status (0xf0)" to "Drive Slot / Bay #0xf0"
            response['specific_info']['fru_id'] = fru+" #"+common['Sensor ID'].split('(')[1][:-1]
        else:
            pass

        return response

    def _create_node_fru_json_message(self, specifics):
        """Creates JSON response to be sent out to Node Controller Message
           Handler for further validation"""
        resource_type = "node:fru:{0}".format(self.fru_node_request)
        epoch_time = str(calendar.timegm(time.gmtime()))
        if socket.gethostname().find('.') >= 0:
            host_id = socket.gethostname()
        else:
            host_id = socket.gethostbyaddr(socket.gethostname())[0]
        response = {
          "alert_type":"GET",
          "severity":"informational",
          "host_id": host_id,
          "instance_id": "*",
          "info": {
            "site_id": self._site_id,
            "rack_id": self._rack_id,
            "node_id": self._node_id,
            "resource_type": resource_type,
            "fetch_time": epoch_time
          },
          "specific_info": specifics
        }

        # Converting raw 'States Asserted' value with readbale value.
        # Example : "Drive Slot / Bay\n                         [Drive Present]"
        # ==> "Drive Slot / Bay : Drive Present"
        if 'States Asserted' in response['specific_info']:
            raw_str = response['specific_info']['States Asserted'].split('\n')
            filter_str = raw_str[0]+raw_str[1].strip()\
                .replace('[',' : ').replace(']','')
            response['specific_info']['States Asserted'] = filter_str

        return response
