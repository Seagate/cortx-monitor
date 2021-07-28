
# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

from framework.base.testcase_base import TestCaseBase
from common import actuator_response_filter


class RealStorCurrentSensorTest(TestCaseBase):
    resource_type = "ENCL:enclosure:sensor:current"
    resource_id = "*"

    def init(self):
        pass

    def filter(self, msg):
        return actuator_response_filter(msg, "enclosure:sensor:current")

    def request(self):
        return enclosure_sensor_message_request(self.resource_type, self.resource_id)

    def response(self, msg):
        current_module_actuator_msg = msg.get("actuator_response_type")

        assert(current_module_actuator_msg is not None)
        assert(current_module_actuator_msg.get("alert_type") is not None)
        assert(current_module_actuator_msg.get("alert_id") is not None)
        assert(current_module_actuator_msg.get("severity") is not None)
        assert(current_module_actuator_msg.get("host_id") is not None)
        assert(current_module_actuator_msg.get("info") is not None)
        assert(current_module_actuator_msg.get("specific_info") is not None)

        info = current_module_actuator_msg.get("info")
        assert(info.get("site_id") is not None)
        assert(info.get("node_id") is not None)
        assert(info.get("cluster_id") is not None)
        assert(info.get("rack_id") is not None)
        assert(info.get("resource_type") is not None)
        assert(info.get("event_time") is not None)
        assert(info.get("resource_id") is not None)

        specific_info = current_module_actuator_msg.get("specific_info")
        generic_specific_info(specific_info)


class RealStorVoltageSensorTest(TestCaseBase):
    resource_type = "ENCL:enclosure:sensor:voltage"
    resource_id = "*"

    def init(self):
        pass

    def filter(self, msg):
        return actuator_response_filter(msg, "enclosure:sensor:voltage")

    def request(self):
        return enclosure_sensor_message_request(self.resource_type, self.resource_id)

    def response(self, msg):
        voltage_module_actuator_msg = msg.get("actuator_response_type")

        assert(voltage_module_actuator_msg is not None)
        assert(voltage_module_actuator_msg.get("alert_type") is not None)
        assert(voltage_module_actuator_msg.get("alert_id") is not None)
        assert(voltage_module_actuator_msg.get("severity") is not None)
        assert(voltage_module_actuator_msg.get("host_id") is not None)
        assert(voltage_module_actuator_msg.get("info") is not None)
        assert(voltage_module_actuator_msg.get("specific_info") is not None)

        info = voltage_module_actuator_msg.get("info")
        assert(info.get("site_id") is not None)
        assert(info.get("node_id") is not None)
        assert(info.get("cluster_id") is not None)
        assert(info.get("rack_id") is not None)
        assert(info.get("resource_type") is not None)
        assert(info.get("event_time") is not None)
        assert(info.get("resource_id") is not None)

        specific_info = voltage_module_actuator_msg.get("specific_info")
        generic_specific_info(specific_info)


class RealStorTemperatureSensorTest(TestCaseBase):
    resource_type = "ENCL:enclosure:sensor:temperature"
    resource_id = "*"

    def init(self):
        pass

    def filter(self, msg):
        return actuator_response_filter(msg, "enclosure:sensor:temperature")

    def request(self):
        return enclosure_sensor_message_request(self.resource_type, self.resource_id)

    def response(self, msg):
        temperature_module_actuator_msg = msg.get("actuator_response_type")

        assert(temperature_module_actuator_msg is not None)
        assert(temperature_module_actuator_msg.get("alert_type") is not None)
        assert(temperature_module_actuator_msg.get("alert_id") is not None)
        assert(temperature_module_actuator_msg.get("severity") is not None)
        assert(temperature_module_actuator_msg.get("host_id") is not None)
        assert(temperature_module_actuator_msg.get("info") is not None)
        assert(temperature_module_actuator_msg.get("specific_info") is not None)

        info = temperature_module_actuator_msg.get("info")
        assert(info.get("site_id") is not None)
        assert(info.get("node_id") is not None)
        assert(info.get("cluster_id") is not None)
        assert(info.get("rack_id") is not None)
        assert(info.get("resource_type") is not None)
        assert(info.get("event_time") is not None)
        assert(info.get("resource_id") is not None)

        specific_info = temperature_module_actuator_msg.get("specific_info")
        generic_specific_info(specific_info)


def generic_specific_info(specific_info):
    for resource in specific_info:
        assert(resource.get("drawer_id_numeric") is not None)
        assert(resource.get("sensor_type") is not None)
        assert(resource.get("container") is not None)
        assert(resource.get("enclosure_id") is not None)
        assert(resource.get("durable_id") is not None)
        assert(resource.get("value") is not None)
        assert(resource.get("status") is not None)
        assert(resource.get("controller_id_numeric") is not None)
        assert(resource.get("object_name") is not None)
        assert(resource.get("container_numeric") is not None)
        assert(resource.get("controller_id") is not None)
        assert(resource.get("sensor_type_numeric") is not None)
        assert(resource.get("sensor_name") is not None)
        assert(resource.get("drawer_id") is not None)
        assert(resource.get("status_numeric") is not None)


def enclosure_sensor_message_request(resource_type, resource_id):
    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username": "JohnDoe",
        "signature": "None",
        "time": "2015-05-29 14:28:30.974749",
        "expires": 500,

        "message": {
            "sspl_ll_msg_header": {
                "schema_version": "1.0.0",
                "sspl_version": "1.0.0",
                "msg_version": "1.0.0"
            },
            "sspl_ll_debug": {
                "debug_component": "sensor",
                "debug_enabled": True
            },
            "request_path": {
                "site_id": "1",
                "rack_id": "1",
                "cluster_id": "1",
                "node_id": "1"
            },
            "response_dest": {},
            "actuator_request_type": {
                "storage_enclosure": {
                    "enclosure_request": resource_type,
                    "resource": resource_id
                }
            }
        }
    }
    return egressMsg


test_list = [RealStorCurrentSensorTest, RealStorVoltageSensorTest, RealStorTemperatureSensorTest]
