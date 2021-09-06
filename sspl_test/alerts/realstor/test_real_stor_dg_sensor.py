# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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
from common import check_sspl_ll_is_running, get_fru_response


def init(args):
    pass

def test_real_stor_dg_sensor(agrs):
    check_sspl_ll_is_running()
    dg_sensor_message_request("enclosure:cortx:disk_group")
    ingress_msg_type = "sensor_response_type"
    ingress_msg = get_fru_response("enclosure:cortx:disk_group", "*",
        ingress_msg_type)
    dg_sensor_msg = ingress_msg.get(ingress_msg_type)
    assert(dg_sensor_msg is not None)
    assert(dg_sensor_msg.get("alert_type") is not None)
    assert(dg_sensor_msg.get("alert_id") is not None)
    assert(dg_sensor_msg.get("severity") is not None)
    assert(dg_sensor_msg.get("host_id") is not None)
    assert(dg_sensor_msg.get("info") is not None)

    dg_sensor_info = dg_sensor_msg.get("info")
    assert(dg_sensor_info.get("resource_type") is not None)
    assert(dg_sensor_info.get("event_time") is not None)
    assert(dg_sensor_info.get("resource_id") is not None)

    dg_sensor_specific_info = dg_sensor_msg.get("specific_info")
    assert(dg_sensor_specific_info is not None)
    assert(dg_sensor_specific_info.get("cvg_name") == 'A01')
    assert(dg_sensor_specific_info.get("cvg_id") == 0)
    assert(dg_sensor_specific_info.get("object_name") is not None)
    assert(dg_sensor_specific_info.get("name") is not None)
    assert(dg_sensor_specific_info.get("size") is not None)
    assert(dg_sensor_specific_info.get("freespace") is not None)
    assert(dg_sensor_specific_info.get("storage_type") is not None)
    assert(dg_sensor_specific_info.get("pool") is not None)
    assert(dg_sensor_specific_info.get("pool_serial_number") is not None)
    assert(dg_sensor_specific_info.get("pool_percentage") is not None)
    assert(dg_sensor_specific_info.get("owner") is not None)
    assert(dg_sensor_specific_info.get("raidtype") is not None)
    assert(dg_sensor_specific_info.get("status") is not None)
    assert(dg_sensor_specific_info.get("create_date") is not None)
    assert(dg_sensor_specific_info.get("disk_description") is not None)
    assert(dg_sensor_specific_info.get("serial_number") is not None)
    assert(dg_sensor_specific_info.get("pool_sector_format") is not None)
    assert(dg_sensor_specific_info.get("health") is not None)
    assert(dg_sensor_specific_info.get("health_reason") is not None)
    assert(dg_sensor_specific_info.get("health_recommendation") is not None)

def dg_sensor_message_request(resource_type):
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

test_list = [test_real_stor_dg_sensor]
