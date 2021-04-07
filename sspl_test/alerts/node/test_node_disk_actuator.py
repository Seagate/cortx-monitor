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
import time
import sys

from default import world
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests
from common import check_sspl_ll_is_running


def init(args):
    pass

def test_node_disk_module_actuator(agrs):
    print("Enters into test_node_disk_module_actuator")
    check_sspl_ll_is_running()
    disk_actuator_message_request("NDHW:node:fru:disk")
    disk_actuator_msg = None
    time.sleep(10)
    ingressMsg = {}
    for i in range(10):
        if world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
            time.sleep(2)
        while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
            ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
            time.sleep(0.1)
            print("Received: %s " % ingressMsg)
            try:
                # Make sure we get back the message type that matches the request
                msg_type = ingressMsg.get("actuator_response_type")
                if msg_type["info"]["resource_type"] == "node:fru:disk":
                    disk_actuator_msg = msg_type
                    break
            except Exception as exception:
                time.sleep(0.1)
                print(exception)

        if disk_actuator_msg:
            break
        time.sleep(1)

    assert(disk_actuator_msg is not None)
    assert(disk_actuator_msg.get("alert_type") is not None)
    # assert(disk_actuator_msg.get("alert_id") is not None)
    assert(disk_actuator_msg.get("severity") is not None)
    assert(disk_actuator_msg.get("host_id") is not None)
    assert(disk_actuator_msg.get("info") is not None)

    disk_actuator_info = disk_actuator_msg.get("info")
    assert(disk_actuator_info.get("site_id") is not None)
    assert(disk_actuator_info.get("node_id") is not None)
    # assert(disk_actuator_info.get("cluster_id") is not None)
    assert(disk_actuator_info.get("rack_id") is not None)
    assert(disk_actuator_info.get("resource_type") is not None)
    assert(disk_actuator_info.get("event_time") is not None)
    assert(disk_actuator_info.get("resource_id") is not None)

    disk_actuator_specific_infos = disk_actuator_msg.get("specific_info")
    for disk_actuator_specific_info in disk_actuator_specific_infos:
        assert(disk_actuator_specific_info is not None)
        assert(disk_actuator_specific_info.get("Sensor Type (Discrete)") is not None)
        assert(disk_actuator_specific_info.get("resource_id") is not None)
        if "States Asserted" in disk_actuator_specific_info:
            assert(disk_actuator_specific_info.get("States Asserted") is not None)

def disk_actuator_message_request(resource_type):
    egressMsg = {
	"username": "sspl-ll",
	"expires": 3600,
	"description": "Seagate Storage Platform Library - Low Level - Actuator Request",
	"title": "SSPL-LL Actuator Request",
	"signature": "None",
	"time": "2018-07-31 04:08:04.071170",
	"message": {
		"sspl_ll_debug": {
			"debug_component": "sensor",
			"debug_enabled": True
		},
		"sspl_ll_msg_header": {
			"msg_version": "1.0.0",
			"uuid": "9e6b8e53-10f7-4de0-a9aa-b7895bab7774",
			"schema_version": "1.0.0",
			"sspl_version": "1.0.0"
		},
		"actuator_request_type": {
			"node_controller": {
				"node_request": resource_type,
				"resource": "*"
			}
		}
	}
    }
    world.sspl_modules[EgressProcessorTests.name()]._write_internal_msgQ(EgressProcessorTests.name(), egressMsg)

test_list = [test_node_disk_module_actuator]
