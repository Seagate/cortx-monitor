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
from lettuce import *

import json
import os
import psutil
import time

# Add the top level directory to the sys.path to access classes
topdir = os.path.dirname(os.path.dirname(os.path.dirname \
            (os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, topdir)


from test.automated.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor


@step('Given that SSPL is running')
def given_that_sspl_is_running(step):
    # Check that the state for sspl service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspld" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['cmdline', 'status'])
            if "sspld" in str(pinfo['cmdline']) and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()


@step('When I send in the fan module sensor message to request the current "([^"]*)" data')
def when_i_send_in_the_fan_module_sensor_message_to_request_the_current_sensor_type_data(step, resource_type):
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
            "sensor_request_type": {
                "enclosure_alert": {
                        "info": {
                            "resource_type": resource_type
                    }
                }
            }
        }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)


@step('Then I get the fan module sensor JSON response message')
def then_i_get_the_fan_module__sensor_json_response_message(step):
    fan_module_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: {0}".format(ingressMsg))
        try:
            # Make sure we get back the message type that matches the request
            fan_module_sensor_msg = ingressMsg.get("sensor_response_type")
            # fan_module_sensor_msg = msg_type["enclosure_fan_module_alert"]
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(fan_module_sensor_msg is not None)
    assert(fan_module_sensor_msg.get("alert_type") is not None)
    assert(fan_module_sensor_msg.get("alert_id") is not None)
    assert(fan_module_sensor_msg.get("severity") is not None)
    assert(fan_module_sensor_msg.get("host_id") is not None)
    assert(fan_module_sensor_msg.get("info") is not None)

    fan_module_info = fan_module_sensor_msg.get("info")
    assert(fan_module_info.get("site_id") is not None)
    assert(fan_module_info.get("node_id") is not None)
    assert(fan_module_info.get("cluster_id") is not None)
    assert(fan_module_info.get("rack_id") is not None)
    assert(fan_module_info.get("resource_type") is not None)
    assert(fan_module_info.get("event_time") is not None)
    assert(fan_module_info.get("resource_id") is not None)

    fru_specific_info = fan_module_sensor_msg.get("specific_info", {})
    if fru_specific_info:
        assert(fru_specific_info.get("durable-id") is not None)
        assert(fru_specific_info.get("status") is not None)
        assert(fru_specific_info.get("name") is not None)
        assert(fru_specific_info.get("enclosure-id") is not None)
        assert(fru_specific_info.get("health") is not None)
        assert(fru_specific_info.get("health-reason") is not None)
        assert(fru_specific_info.get("location") is not None)
        assert(fru_specific_info.get("health-recommendation") is not None)
        assert(fru_specific_info.get("position") is not None)

    fans = fan_module_sensor_msg.get("specific_info").get("fans", [])
    if fans:
        for fan in fans:
            assert(fan.get("durable-id") is not None)
            assert(fan.get("status") is not None)
            assert(fan.get("name") is not None)
            assert(fan.get("speed") is not None)
            assert(fan.get("locator-led") is not None)
            assert(fan.get("position") is not None)
            assert(fan.get("location") is not None)
            assert(fan.get("part-number") is not None)
            assert(fan.get("serial-number") is not None)
            assert(fan.get("fw-revision") is not None)
            assert(fan.get("hw-revision") is not None)
            assert(fan.get("health") is not None)
            assert(fan.get("health-reason") is not None)
            assert(fan.get("health-recommendation") is not None)

