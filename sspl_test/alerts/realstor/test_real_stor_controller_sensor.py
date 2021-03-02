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

from default import world
from rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor


def init(args):
    pass

def test_real_stor_controller_sensor(agrs):
    check_sspl_ll_is_running()
    controller_sensor_message_request("enclosure:fru:controller")
    controller_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:fru:controller":
                controller_sensor_msg = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
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
    assert(info.get("description") is not None)

    specific_info = controller_sensor_msg.get("specific_info")
    assert(specific_info.get("object_name") is not None)
    assert(specific_info.get("controller_id") is not None)
    assert(specific_info.get("serial_number") is not None)
    assert(specific_info.get("hardware_version") is not None)
    assert(specific_info.get("cpld_version") is not None)
    assert(specific_info.get("mac_address") is not None)
    assert(specific_info.get("node_wwn") is not None)
    assert(specific_info.get("ip_address") is not None)
    assert(specific_info.get("ip_subnet_mask") is not None)
    assert(specific_info.get("ip_gateway") is not None)
    assert(specific_info.get("disks") is not None)
    assert(specific_info.get("number_of_storage_pools") is not None)
    assert(specific_info.get("virtual_disks") is not None)
    assert(specific_info.get("host_ports") is not None)
    assert(specific_info.get("drive_channels") is not None)
    assert(specific_info.get("drive_bus_type") is not None)
    assert(specific_info.get("status") is not None)
    assert(specific_info.get("failed_over") is not None)
    assert(specific_info.get("fail_over_reason") is not None)
    assert(specific_info.get("vendor") is not None)
    assert(specific_info.get("model") is not None)
    assert(specific_info.get("platform_type") is not None)
    assert(specific_info.get("write_policy") is not None)
    assert(specific_info.get("description") is not None)
    assert(specific_info.get("part_number") is not None)
    assert(specific_info.get("revision") is not None)
    assert(specific_info.get("mfg_vendor_id") is not None)
    assert(specific_info.get("locator_led") is not None)
    assert(specific_info.get("health") is not None)
    assert(specific_info.get("health_reason") is not None)
    assert(specific_info.get("position") is not None)
    assert(specific_info.get("redundancy_mode") is not None)
    assert(specific_info.get("redundancy_status") is not None)
    assert(specific_info.get("compact_flash") is not None)
    assert(specific_info.get("network_parameters") is not None)
    assert(specific_info.get("expander_ports") is not None)
    assert(specific_info.get("expanders") is not None)
    assert(specific_info.get("port") is not None)

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
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

def controller_sensor_message_request(resource_type):
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

test_list = [test_real_stor_controller_sensor]
