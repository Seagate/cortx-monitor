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

import json
import os
import psutil
import time
import sys

from default import world
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests
from framework.utils.conf_utils import Conf, SSPL_TEST_CONF, NODE_ID_KEY
from framework.base.sspl_constants import DEFAULT_NODE_ID


def init(args):
    pass

def test_real_stor_sensor_current(agrs):
    check_sspl_ll_is_running()
    target_node_id = Conf.get(SSPL_TEST_CONF, NODE_ID_KEY, DEFAULT_NODE_ID)
    enclosure_sensor_message_request("ENCL:enclosure:sensor:current", "*", target_node_id)
    enclosure_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:sensor:current":
                current_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)

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


def test_real_stor_sensor_voltage(agrs):
    check_sspl_ll_is_running()
    target_node_id = Conf.get(SSPL_TEST_CONF, NODE_ID_KEY, DEFAULT_NODE_ID)
    enclosure_sensor_message_request("ENCL:enclosure:sensor:voltage", "*", target_node_id)
    enclosure_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:sensor:voltage":
                voltage_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print(exception)

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


def test_real_stor_sensor_temperature(agrs):
    check_sspl_ll_is_running()
    target_node_id = Conf.get(SSPL_TEST_CONF, NODE_ID_KEY, DEFAULT_NODE_ID)
    enclosure_sensor_message_request("ENCL:enclosure:sensor:temperature", "*", target_node_id)
    enclosure_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:sensor:temperature":
                temperature_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print(exception)

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

def check_sspl_ll_is_running():
    # Check that the state for sspl service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspl_ll_d" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['cmdline', 'status'])
            if "sspl_ll_d" in str(pinfo['cmdline']) and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()

def enclosure_sensor_message_request(resource_type, resource_id, target_node_id=DEFAULT_NODE_ID):

    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "2015-05-29 14:28:30.974749",
        "expires" : 500,

        "message" : {
            "sspl_ll_msg_header": {
                "schema_version": "1.0.0",
                "sspl_version": "1.0.0",
                "msg_version": "1.0.0"
            },
             "sspl_ll_debug": {
                "debug_component" : "sensor",
                "debug_enabled" : True
            },
            "request_path": {
                "site_id": "1",
                "rack_id": "1",
                "cluster_id": "1",
                "node_id": "1"
            },
            "response_dest": {},
            "target_node_id": target_node_id,
            "actuator_request_type": {
                "storage_enclosure": {
                    "enclosure_request": resource_type,
                    "resource": resource_id
                }
            }
        }
    }
    world.sspl_modules[EgressProcessorTests.name()]._write_internal_msgQ(EgressProcessorTests.name(), egressMsg)

test_list = [test_real_stor_sensor_current, test_real_stor_sensor_voltage, test_real_stor_sensor_temperature]
