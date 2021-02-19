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

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

def init(args):
    pass

def test_real_stor_disk_sensor(agrs):
    check_sspl_ll_is_running()
    disk_sensor_message_request("enclosure:fru:disk")
    disk_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            time.sleep(0.1)
            if msg_type['info']['resource_type'] == "enclosure:fru:disk":
                disk_sensor_msg = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)

    assert(disk_sensor_msg is not None)
    assert(disk_sensor_msg.get("alert_type") is not None)
    assert(disk_sensor_msg.get("alert_id") is not None)
    assert(disk_sensor_msg.get("severity") is not None)
    assert(disk_sensor_msg.get("host_id") is not None)
    assert(disk_sensor_msg.get("info") is not None)

    disk_sensor_info = disk_sensor_msg.get("info")
    assert(disk_sensor_info.get("site_id") is not None)
    assert(disk_sensor_info.get("node_id") is not None)
    assert(disk_sensor_info.get("cluster_id") is not None)
    assert(disk_sensor_info.get("rack_id") is not None)
    assert(disk_sensor_info.get("resource_type") is not None)
    assert(disk_sensor_info.get("event_time") is not None)
    assert(disk_sensor_info.get("resource_id") is not None)
    assert(disk_sensor_info.get("description") is not None)

    disk_sensor_specific_info = disk_sensor_msg.get("specific_info")
    assert(disk_sensor_specific_info is not None)
    assert(disk_sensor_specific_info.get("description") is not None)
    assert(disk_sensor_specific_info.get("slot") is not None)
    assert(disk_sensor_specific_info.get("status") is not None)
    assert(disk_sensor_specific_info.get("architecture") is not None)
    assert(disk_sensor_specific_info.get("serial_number") is not None)
    assert(disk_sensor_specific_info.get("size") is not None)
    assert(disk_sensor_specific_info.get("vendor") is not None)
    assert(disk_sensor_specific_info.get("model") is not None)
    assert(disk_sensor_specific_info.get("revision") is not None)
    assert(disk_sensor_specific_info.get("temperature") is not None)
    assert(disk_sensor_specific_info.get("LED_status") is not None)
    assert(disk_sensor_specific_info.get("locator_LED") is not None)
    assert(disk_sensor_specific_info.get("blink") is not None)
    assert(disk_sensor_specific_info.get("smart") is not None)
    assert(disk_sensor_specific_info.get("health") is not None)
    assert(disk_sensor_specific_info.get("health_reason") is not None)
    assert(disk_sensor_specific_info.get("health_recommendation") is not None)
    assert(disk_sensor_specific_info.get("enclosure_family") is not None)
    assert(disk_sensor_specific_info.get("enclosure_id") is not None)
    assert(disk_sensor_specific_info.get("enclosure_wwn") is not None)

def check_sspl_ll_is_running():
    # Check that the state for sspl_ll service is active
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


def disk_sensor_message_request(resource_type):
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

test_list = [test_real_stor_disk_sensor]
