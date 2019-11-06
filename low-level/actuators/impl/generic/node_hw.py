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

import json
from actuators.impl.actuator import Actuator
from framework.base.debug import Debug
from framework.utils.service_logging import logger
from framework.base.sspl_constants import AlertTypes, SensorTypes, SeverityTypes


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

    def __init__(self, executor, conf_reader):
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
        self._executor = executor
        self.fru_specific_info = {}
        self._resource_id = ""
        self._sensor_type = ""

    def initialize(self):
        """Performs basic Node HW actuator initialization"""
        sensor_id_map = self._executor.get_fru_list_by_type(
            ['fan', 'power supply', 'drive slot / bay'],
            sensor_id_map={})
        self.sensor_id_map = sensor_id_map

    def _get_fru_instances(self, fru, fru_instance):
        """Get the fru information based on fru_type and instance"""
        response = None
        sensor_props_list = {}
        fru_info_dict = {}
        if fru_instance == "*":
            try:
                fru_dict = self.sensor_id_map[fru.lower()]
                for sensor_id in fru_dict.values():
                    if sensor_id == '':
                        continue
                    sensor_common_info, sensor_specific_info = self._executor.get_sensor_props(sensor_id)
                    self.fru_specific_info[sensor_id] = sensor_specific_info

                if self.fru_specific_info is not None:
                    response = self._parse_fru_info()
            except KeyError as e:
                logger.error('NodeHWactuator, _get_fru_instances, \
                                Unable to process the FRU type: %s' % e)
                return
            except Exception as e:
                logger.exception('NodeHWactuator, _get_fru_instances, \
                                Error occured during request parsing %s' % e)
                return
        return response

    def _parse_fru_info(self):
        """Parses fan information"""
        fru_type = "fan"
        specific_info = None
        specifics = []
        for sensor_id, fru_info in self.fru_specific_info.iteritems():
            specific_info = dict()
            for fru_key,fru_value in fru_info.iteritems():
                specific_info[fru_key] = fru_value
            specific_info["resource_id"] = sensor_id
            specifics.append(specific_info)
        response = self._create_node_fru_json_message(specifics)
        return response

    def perform_request(self, json_msg):
        """Performs the Node server request

        @return: The response string from performing the request
        """
        response = ""
        node_request = json_msg.get("node_controller")
        node_request_instance = node_request.get("node_request").split(":")[:3]

        if node_request_instance == ['NDHW', 'node', 'fru']:
            response = self._process_fru_request(node_request)
        elif node_request_instance == ['NDHW', 'node', 'sensor']:
            response = self._process_sensor_request(node_request)

        return response

    def _process_fru_request(self, node_request):
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
            common, specific = self._executor.get_sensor_props(sensor_id)
            response = self._create_node_fru_json_message(specific)
            response['instance_id'] = fru_instance
            response['info']['resource_id'] = sensor_id

            # Converting Fru ID From "HDD 0 Status (0xf0)" to "Drive Slot / Bay #0xf0"
            response['specific_info']['fru_id'] = fru+" #"+common['Sensor ID'].split('(')[1][:-1]
        else:
            response = self._get_fru_instances(fru, fru_instance)

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
            "resource_id": "*",
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

    def _process_sensor_request(self, node_request):
        response = dict()
        # todo : validate on which node request commands are executing.

        # "node_request": "NDHW:node:sensor:Temperature"
        # "resource": "* or PS1 Temperature"
        self._sensor_type = node_request.get('node_request').split(":")[3]
	self._resource_id = node_request.get('resource')
        if self._sensor_type.lower() in list(map(lambda sensor_item: sensor_item.value.lower(), SensorTypes)):
            # fetch generic node info
            self._build_generic_info(response)
            # fetch specific info
            self._build_sensor_info(response, self._sensor_type, self._resource_id)
        else:
            logger.error("Error: Unsupported sensor type {}".format(self._sensor_type))

        return response

    def _get_sensor_properties(self, sensor_name):
        """
        Get all the properties of a sensor.
        Returns a tuple (common, specific) where common is a dict of common sensor properties and
        their values for this sensor, and specific is a dict of the properties specific to this sensor
        e.g. ipmitool sensor get 'PS1 Temperature'
        Locating sensor record...
         Sensor ID              : PS1 Temperature (0x5c)
         Entity ID             : 10.1
         Sensor Type (Threshold)  : Temperature
         Sensor Reading        : 16 (+/- 0) degrees C
         Status                : ok
         Lower Non-Recoverable : na
         Lower Critical        : na
         Lower Non-Critical    : na
         Upper Non-Critical    : 55.000
         Upper Critical        : 60.000
         Upper Non-Recoverable : na
         Positive Hysteresis   : 2.000
         Negative Hysteresis   : 2.000
         Assertion Events      :
         Assertions Enabled    : unc+ ucr+
         Deassertions Enabled  : unc+ ucr+
        """
        sensor_get_response, return_code = self._executor._run_ipmitool_subcommand("sensor get '{0}'".format(sensor_name))
        if return_code != 0:
            msg = "sensor get '{0}' : command failed with error {1}".format(sensor_name, sensor_get_response)
            logger.error(msg)
        return self._response_to_dict(sensor_get_response)

    def _build_generic_info(self, response):
        """
        Build json with generic information
        :param response:
        :return:
        """
	response['instance_id'] = self._resource_id
        response['alert_type'] = AlertTypes.GET.value
        response['severity'] = SeverityTypes.INFORMATIONAL.value
        response['info'] = {
            "site_id": self._site_id,
            "rack_id": self._rack_id,
            "node_id": self._node_id,
            "resource_type": "node:sensor:" + self._sensor_type.lower(),
            "resource_id": self._resource_id,
            "fetch_time": str(calendar.timegm(time.gmtime())),
        }

        # fetch host details
        self._build_host_details(response)

    def _build_host_details(self, response):
        """
        build json with host details
        :param response:
        :return:
        """
        # fetch host id from socket set in response
        if socket.gethostname().find('.') >= 0:
            _host_id = socket.gethostname()
        else:
            _host_id = socket.gethostbyaddr(socket.gethostname())[0]
        response['host_id'] = _host_id

    def _build_sensor_info(self, response, sensor_type, sensor_name):
        """
        Build json with sensor common and specific information
        :param response:
        :param sensor_type:
        :param sensor_name:
        :return:
        """
        many_sensors = False
        if sensor_name == "*":
            many_sensors = True
            sdr_type_response, return_code = self._executor._run_ipmitool_subcommand(
                "sdr type '{0}'".format(sensor_type))

        else:
            sdr_type_response, return_code = self._executor._run_ipmitool_subcommand(
                "sdr type '{0}'".format(sensor_type),
                grep_args=sensor_name)

        if return_code != 0:
            msg = "sdr type '{0}' : command failed with error {1}".format(sensor_type, sdr_type_response)
            logger.error(msg)
        else:
            if many_sensors:
                # for all sensors specific info response will be list
                response['specific_info'] = self._response_to_dict(sdr_type_response, split_char='|',
                                                                   dict_keys=['resource_id', 'sensor_number',
                                                                              'sensor_status', 'entity_id_instance',
                                                                              'sensor_reading'], many_sensors=True)
            else:
                # for specific sensor specific info response will be dict
                response['specific_info'] = self._response_to_dict(sdr_type_response, split_char='|',
                                                                   dict_keys=['resource_id', 'sensor_number',
                                                                              'sensor_status', 'entity_id_instance',
                                                                              'sensor_reading'])
                response['specific_info'].update(self._get_sensor_properties(sensor_name))

    def _response_to_dict(self, data, split_char=':', dict_keys=None, many_sensors=False):
        """
        Take response data and split with given split char, Convert it into readable dict.
        :param data: String with multiple lines
        :param split_char: char to split with
        :param dict_keys: List of keys to be used in properties dict
        :param many_sensors: Many lines for sensor name = '*'
        :return:
        """
        many_sensors_data = []
        properties = {}
        try:
            # check if data is tuple, convert to string
            if isinstance(data, tuple):
                data_str = ''.join(data)
            else:
                data_str = data

            # from properties list split out key and values.
            for line in data_str.split("\n"):
                if split_char in line:
                    if dict_keys is not None:
                        inner_dict = dict()
                        result = line.split(split_char)
                        # validate result size and dict key size are same
                        if len(result) == len(dict_keys):
                            for i in range(len(result)):
                                inner_dict[dict_keys[i]] = result[i].strip()
                        # This line will break loop by reading single line of result
                        # If user trying to fetch only specific sensor data
                        if not many_sensors:
                            properties = inner_dict
                            break
                        many_sensors_data.append(inner_dict)
                    else:
                        if len(line.split(split_char)) >= 2:
                            properties[line.split(split_char)[0].strip()] = line.split(split_char)[1].strip()
        except KeyError as e:
            msg = "Error in parsing response: {}".format(e)
            logger.error(msg)

        if many_sensors:
            return many_sensors_data

        return properties
