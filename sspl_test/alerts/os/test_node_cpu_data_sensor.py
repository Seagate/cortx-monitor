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
from time import sleep
import sys

from default import world
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests
from common import check_sspl_ll_is_running, get_fru_response


def init(args):
    pass

def test_cpu_data_sensor(args):
    resource_type = "server:hw:cpu_usage"
    instance_id = "*"
    ingress_msg_type="sensor_response_type"
    check_sspl_ll_is_running()
    node_data_sensor_message_request(resource_type)
    ingress_msg = get_fru_response(
        resource_type, instance_id, ingress_msg_type)

    cpu_data_msg = ingress_msg.get(ingress_msg_type)
    assert(cpu_data_msg is not None)
    assert(cpu_data_msg.get("alert_type") is not None)
    assert(cpu_data_msg.get("alert_id") is not None)
    assert(cpu_data_msg.get("severity") is not None)
    assert(cpu_data_msg.get("host_id") is not None)
    assert(cpu_data_msg.get("info") is not None)
    assert(cpu_data_msg.get("specific_info") is not None)

    info = cpu_data_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)
    assert(info.get("description") is not None)

    specific_info = cpu_data_msg.get("specific_info")
    assert(specific_info.get("systemTime") is not None)
    assert(specific_info.get("interruptTime") is not None)
    assert(specific_info.get("userTime") is not None)
    assert(specific_info.get("idleTime") is not None)
    assert(specific_info.get("csps") is not None)
    assert(specific_info.get("iowaitTime") is not None)
    assert(specific_info.get("niceTime") is not None)
    assert(specific_info.get("cpu_usage") is not None)
    assert(specific_info.get("coreData") is not None)
    assert(specific_info.get("localtime") is not None)
    assert(specific_info.get("softirqTime") is not None)
    assert(specific_info.get("stealTime") is not None)

def node_data_sensor_message_request(sensor_type):
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
                "node_data": {
                    "sensor_type": sensor_type
                }
            }
        }
    }

    world.sspl_modules[EgressProcessorTests.name()]._write_internal_msgQ(EgressProcessorTests.name(), egressMsg)


test_list = [test_cpu_data_sensor]
