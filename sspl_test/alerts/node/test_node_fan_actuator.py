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

# -*- coding: utf-8 -*-
import json
import os
import psutil
import time
import sys

from cortx.sspl.sspl_test.alerts.self_hw.self_hw_utilities import run_cmd, is_virtual
from cortx.sspl.sspl_test.default import *
from cortx.sspl.sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from cortx.sspl.sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from cortx.sspl.sspl_test.common import check_sspl_ll_is_running

UUID="16476007-a739-4785-b5c6-f3de189cdf11"

# Check which fans are OK
test_resource = "*" # Use * if virtual machine
result = run_cmd('ipmitool sdr type Fan')
if result and not is_virtual():
        for resource in result:
            if 'ok' in resource.decode().lower():
                # this is the first ok resource, use it in case of real HW
                test_resource = resource.decode().split('|')[0].strip()
                break

def init(args):
    pass

def test_node_fan_module_actuator(agrs):
    check_sspl_ll_is_running()
    fan_actuator_message_request("NDHW:node:fru:fan", str(test_resource))
    fan_module_actuator_msg = None
    time.sleep(6)
    ingressMsg = {}
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "node:fru:fan":
                fan_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)

    assert(ingressMsg.get("sspl_ll_msg_header").get("uuid") == UUID)

    assert(fan_module_actuator_msg is not None)
    assert(fan_module_actuator_msg.get("alert_type") is not None)
    assert(fan_module_actuator_msg.get("severity") is not None)
    assert(fan_module_actuator_msg.get("host_id") is not None)
    assert(fan_module_actuator_msg.get("info") is not None)
    assert(fan_module_actuator_msg.get("instance_id") is not None)

    fan_module_info = fan_module_actuator_msg.get("info")
    assert(fan_module_info.get("site_id") is not None)
    assert(fan_module_info.get("node_id") is not None)
    assert(fan_module_info.get("rack_id") is not None)
    assert(fan_module_info.get("resource_type") is not None)
    assert(fan_module_info.get("event_time") is not None)
    assert(fan_module_info.get("resource_id") is not None)

    fru_specific_infos = fan_module_actuator_msg.get("specific_info", {})

    if fru_specific_infos and fan_module_info.get("resource_id") == "*":
        for fru_specific_info in fru_specific_infos:
            resource_id = fru_specific_info.get("resource_id")
            if "Fan Fail" in resource_id:
                assert(fru_specific_info.get("Sensor Type (Discrete)") is not None)
                assert(fru_specific_info.get("resource_id") is not None)
            elif "System Fan" in resource_id:
                assert(fru_specific_info.get("Status") is not None)
                assert(fru_specific_info.get("Sensor Type (Threshold)") is not None)
                assert(fru_specific_info.get("Sensor Reading") is not None)
                assert(fru_specific_info.get("Lower Non-Recoverable") is not None)
                assert(fru_specific_info.get("Assertions Enabled") is not None)
                assert(fru_specific_info.get("Upper Non-Critical") is not None)
                assert(fru_specific_info.get("Upper Non-Recoverable") is not None)
                assert(fru_specific_info.get("Positive Hysteresis") is not None)
                assert(fru_specific_info.get("Lower Critical") is not None)
                assert(fru_specific_info.get("Deassertions Enabled") is not None)
                assert(fru_specific_info.get("Lower Non-Critical") is not None)
                assert(fru_specific_info.get("Upper Critical") is not None)
                assert(fru_specific_info.get("Negative Hysteresis") is not None)
                assert(fru_specific_info.get("Assertion Events") is not None)
                assert(fru_specific_info.get("resource_id") is not None)
            else:
                assert(fru_specific_info.get("States Asserted") is not None)
                assert(fru_specific_info.get("Sensor Type (Discrete)") is not None)
                assert(fru_specific_info.get("resource_id") is not None)
    elif fru_specific_infos:
        assert(fru_specific_infos.get("Sensor Type (Threshold)") is not None)
        assert(fru_specific_infos.get("Sensor Reading") is not None)
        assert(fru_specific_infos.get("Status") is not None)
        assert(fru_specific_infos.get("Lower Non_Recoverable") is not None)
        assert(fru_specific_infos.get("Lower Critical") is not None)
        assert(fru_specific_infos.get("Lower Non_Critical") is not None)
        assert(fru_specific_infos.get("Upper Non_Critical") is not None)
        assert(fru_specific_infos.get("Upper Critical") is not None)
        assert(fru_specific_infos.get("Upper Non_Recoverable") is not None)
        assert(fru_specific_infos.get("Positive Hysteresis") is not None)
        assert(fru_specific_infos.get("Negative Hysteresis") is not None)
        assert(fru_specific_infos.get("Assertion Events") is not None)
        assert(fru_specific_infos.get("Assertions Enabled") is not None)
        assert(fru_specific_infos.get("Deassertions Enabled") is not None)
        assert(fru_specific_infos.get("resource_id") is not None)

def fan_actuator_message_request(resource_type, resource_id):
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
                "msg_version": "1.0.0",
                "uuid": UUID
            },
             "sspl_ll_debug": {
                "debug_component" : "sensor",
                "debug_enabled" : True
            },
            "request_path": {
                "site_id": "1",
                "rack_id": "1",
                "node_id": "1"
            },
            "response_dest": {},
            "actuator_request_type": {
                "node_controller": {
                    "node_request": resource_type,
                    "resource": resource_id
                }
            }
        }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_node_fan_module_actuator]
