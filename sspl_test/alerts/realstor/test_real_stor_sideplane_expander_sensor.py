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
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests


def init(args):
    pass

def test_real_stor_sideplane_expander_sensor(agrs):
    check_sspl_ll_is_running()
    sideplane_expander_sensor_message_request("enclosure:hw:sideplane")
    fan_module_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:hw:sideplane":
                sideplane_expander_sensor_msg = ingressMsg.get("sensor_response_type")
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)

    assert(sideplane_expander_sensor_msg is not None)
    assert(sideplane_expander_sensor_msg.get("alert_type") is not None)
    assert(sideplane_expander_sensor_msg.get("alert_id") is not None)
    assert(sideplane_expander_sensor_msg.get("host_id") is not None)
    assert(sideplane_expander_sensor_msg.get("severity") is not None)
    assert(sideplane_expander_sensor_msg.get("info") is not None)

    sideplane_expander_info_data = sideplane_expander_sensor_msg.get("info")
    assert(sideplane_expander_info_data.get("site_id") is not None)
    assert(sideplane_expander_info_data.get("node_id") is not None)
    assert(sideplane_expander_info_data.get("cluster_id") is not None)
    assert(sideplane_expander_info_data.get("rack_id") is not None)
    assert(sideplane_expander_info_data.get("resource_type") is not None)
    assert(sideplane_expander_info_data.get("event_time") is not None)
    assert(sideplane_expander_info_data.get("resource_id") is not None)
    assert(sideplane_expander_info_data.get("description") is not None)

    sideplane_expander_specific_info_data = sideplane_expander_sensor_msg.get("specific_info", {})

    if sideplane_expander_specific_info_data:
        assert(sideplane_expander_specific_info_data.get("position") is not None)
        assert(sideplane_expander_specific_info_data.get("durable_id") is not None)
        assert(sideplane_expander_specific_info_data.get("drawer_id") is not None)
        assert(sideplane_expander_specific_info_data.get("status") is not None)
        assert(sideplane_expander_specific_info_data.get("name") is not None)
        assert(sideplane_expander_specific_info_data.get("enclosure_id") is not None)
        assert(sideplane_expander_specific_info_data.get("health_reason") is not None)
        assert(sideplane_expander_specific_info_data.get("health") is not None)
        assert(sideplane_expander_specific_info_data.get("location") is not None)
        assert(sideplane_expander_specific_info_data.get("health_recommendation") is not None)


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

def sideplane_expander_sensor_message_request(resource_type):
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
    world.sspl_modules[EgressProcessorTests.name()]._write_internal_msgQ(EgressProcessorTests.name(), egressMsg)

test_list = [test_real_stor_sideplane_expander_sensor]
