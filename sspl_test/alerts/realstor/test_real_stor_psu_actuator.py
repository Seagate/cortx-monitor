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

def test_real_stor_psu_actuator(agrs):
    check_sspl_ll_is_running()
    psu_actuator_message_request("ENCL:enclosure:fru:psu")
    psu_actuator_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("actuator_response_type")
            time.sleep(0.1)
            if msg_type['info']['resource_type'] == "enclosure:fru:psu":
                psu_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)

    assert(psu_actuator_msg is not None)
    assert(psu_actuator_msg.get("host_id") is not None)
    assert(psu_actuator_msg.get("alert_type") is not None)
    assert(psu_actuator_msg.get("severity") is not None)
    assert(psu_actuator_msg.get("alert_id") is not None)
    psu_info = psu_actuator_msg.get("info")
    assert(psu_info is not None)
    assert(psu_info.get("site_id") is not None)
    assert(psu_info.get("cluster_id") is not None)
    assert(psu_info.get("rack_id") is not None)
    assert(psu_info.get("node_id") is not None)
    assert(psu_info.get("resource_type") is not None)
    assert(psu_info.get("resource_id") is not None)
    assert(psu_info.get("event_time") is not None)

    psu_actuator_specific_info_array = psu_actuator_msg.get("specific_info")
    for psu_specific_info in psu_actuator_specific_info_array:
        assert(psu_specific_info is not None)
        assert(psu_specific_info.get("dctemp") is not None)
        assert(psu_specific_info.get("dc33v") is not None)
        assert(psu_specific_info.get("fru_shortname") is not None)
        assert(psu_specific_info.get("health_reason") is not None)
        assert(psu_specific_info.get("serial_number") is not None)
        assert(psu_specific_info.get("mfg_date") is not None)
        assert(psu_specific_info.get("dash_level") is not None)
        assert(psu_specific_info.get("dom_id") is not None)
        assert(psu_specific_info.get("dc5i") is not None)
        assert(psu_specific_info.get("enclosure_id") is not None)
        assert(psu_specific_info.get("position_numeric") is not None)
        assert(psu_specific_info.get("durable_id") is not None)
        assert(psu_specific_info.get("configuration_serialnumber") is not None)
        assert(psu_specific_info.get("health") is not None)
        assert(psu_specific_info.get("location") is not None)
        assert(psu_specific_info.get("dc5v") is not None)
        assert(psu_specific_info.get("status_numeric") is not None)
        assert(psu_specific_info.get("revision") is not None)
        assert(psu_specific_info.get("mfg_location") is not None)
        assert(psu_specific_info.get("dc12v") is not None)
        assert(psu_specific_info.get("vendor") is not None)
        assert(psu_specific_info.get("description") is not None)
        assert(psu_specific_info.get("mfg_date_numeric") is not None)
        assert(psu_specific_info.get("object_name") is not None)
        assert(psu_specific_info.get("part_number") is not None)
        assert(psu_specific_info.get("health_recommendation") is not None)
        assert(psu_specific_info.get("health_numeric") is not None)
        assert(psu_specific_info.get("dc12i") is not None)
        assert(psu_specific_info.get("name") is not None)
        assert(psu_specific_info.get("fw_revision") is not None)
        assert(psu_specific_info.get("position") is not None)
        assert(psu_specific_info.get("model") is not None)
        assert(psu_specific_info.get("mfg_vendor_id") is not None)
    


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


def psu_actuator_message_request(resource_type):
    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "2015-05-29 14:28:30.974749",
        "expires" : 500,

        "message": {
        "sspl_ll_debug": {
        "debug_component": "sensor",
        "debug_enabled": True
        },
        "response_dest": {
        },
        "sspl_ll_msg_header": {
        "msg_version": "1.0.0",
        "uuid": "16476007-a739-4785-b5c7-f3de189cdf9d",
        "schema_version": "1.0.0",
        "sspl_version": "1.0.0"
        },
        "request_path": {
                    "site_id": "0",
                    "node_id": "1",
                    "rack_id": "0"
        },
        "actuator_request_type": {
            "storage_enclosure": {
                "enclosure_request": resource_type,
                "resource": "*"
                }
                }
            }
        }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_real_stor_psu_actuator]
