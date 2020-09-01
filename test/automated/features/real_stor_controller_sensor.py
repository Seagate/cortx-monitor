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

import os
import json
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
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

@step('When I send in the controller sensor message to request the current "([^"]*)" data')
def when_i_send_in_the_controller_sensor_message_to_request_the_current_sensor_type_data(step, resource_type):
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

@step('Then I get the controller sensor JSON response message')
def then_i_get_the_controller_sensor_json_response_message(step):

    controller_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            controller_sensor_msg = ingressMsg.get("sensor_response_type")
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(controller_sensor_msg is not None)
    assert(controller_sensor_msg.get("alert_type") is not None)
    assert(controller_sensor_msg.get("alert_id") is not None)
    assert(controller_sensor_msg.get("severity") is not None)
    assert(controller_sensor_msg.get("host_id") is not None)
    assert(controller_sensor_msg.get("info") is not None)
    assert(controller_sensor_msg.get("specific_info") is not None)

    info = controller_sensor_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = controller_sensor_msg.get("specific_info")
    assert(specific_info.get("object-name") is not None)
    assert(specific_info.get("controller-id") is not None)
    assert(specific_info.get("serial-number") is not None)
    assert(specific_info.get("hardware-version") is not None)
    assert(specific_info.get("cpld-version") is not None)
    assert(specific_info.get("mac-address") is not None)
    assert(specific_info.get("node-wwn") is not None)
    assert(specific_info.get("ip-address") is not None)
    assert(specific_info.get("ip-subnet-mask") is not None)
    assert(specific_info.get("ip-gateway") is not None)
    assert(specific_info.get("disks") is not None)
    assert(specific_info.get("number-of-storage-pools") is not None)
    assert(specific_info.get("virtual-disks") is not None)
    assert(specific_info.get("host-ports") is not None)
    assert(specific_info.get("drive-channels") is not None)
    assert(specific_info.get("drive-bus-type") is not None)
    assert(specific_info.get("status") is not None)
    assert(specific_info.get("failed-over") is not None)
    assert(specific_info.get("fail-over-reason") is not None)
    assert(specific_info.get("vendor") is not None)
    assert(specific_info.get("model") is not None)
    assert(specific_info.get("platform-type") is not None)
    assert(specific_info.get("write-policy") is not None)
    assert(specific_info.get("description") is not None)
    assert(specific_info.get("part-number") is not None)
    assert(specific_info.get("revision") is not None)
    assert(specific_info.get("mfg-vendor-id") is not None)
    assert(specific_info.get("locator-led") is not None)
    assert(specific_info.get("health") is not None)
    assert(specific_info.get("health-reason") is not None)
    assert(specific_info.get("position") is not None)
    assert(specific_info.get("redundancy-mode") is not None)
    assert(specific_info.get("redundancy-status") is not None)
    assert(specific_info.get("compact-flash") is not None)
    assert(specific_info.get("network-parameters") is not None)
    assert(specific_info.get("expander-ports") is not None)
    assert(specific_info.get("expanders") is not None)
    assert(specific_info.get("port") is not None)
