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

import time

from common import check_sspl_ll_is_running, get_fru_response, write_to_egress_msgQ


UUID="16476007-a739-4785-b5c6-f3de189cdf12"

def init(args):
    pass

def test_node_fan_module_actuator(agrs):
    check_sspl_ll_is_running()
    instance_id = "*"
    resource_type = "node:fru:fan"
    send_msg_request("NDHW:%s" % resource_type, instance_id)
    ingressMsg = get_fru_response(resource_type, instance_id)

    assert ingressMsg.get("sspl_ll_msg_header").get("uuid") == UUID

    fan_module_actuator_msg = ingressMsg.get("actuator_response_type")
    assert fan_module_actuator_msg is not None
    assert fan_module_actuator_msg.get("alert_type") is not None
    assert fan_module_actuator_msg.get("severity") is not None
    assert fan_module_actuator_msg.get("host_id") is not None
    assert fan_module_actuator_msg.get("info") is not None
    assert fan_module_actuator_msg.get("instance_id") == instance_id

    fan_module_info = fan_module_actuator_msg.get("info")
    assert fan_module_info.get("site_id") is not None
    assert fan_module_info.get("node_id") is not None
    assert fan_module_info.get("rack_id") is not None
    assert fan_module_info.get("resource_type") is not None
    assert fan_module_info.get("event_time") is not None
    assert fan_module_info.get("resource_id") is not None

    fan_specific_infos = fan_module_actuator_msg.get("specific_info")
    assert fan_specific_infos is not None

    if fan_module_info.get("resource_id") == "*":
        for fan_specific_info in fan_specific_infos:
            assert fan_specific_info is not None
            if fan_specific_info.get("ERROR"):
                # Skip any validation on specific info if ERROR seen on FRU
                continue
            resource_id = fan_specific_info.get("resource_id", "")
            if fan_specific_info.get(resource_id):
                assert fan_specific_info.get(resource_id).get("ERROR") is not None
                # Skip any validation on specific info if ERROR seen on sensor
                continue
            if "Fan Fail" in resource_id:
                assert fan_specific_info.get("Sensor Type (Discrete)") is not None
                assert fan_specific_info.get("resource_id") is not None
            else:
                assert fan_specific_info.get("resource_id") is not None
                assert fan_specific_info.get("Sensor Type (Threshold)") is not None
                assert fan_specific_info.get("Sensor Reading") is not None
                assert fan_specific_info.get("Status") is not None
                assert fan_specific_info.get("Lower Non_Recoverable") is not None
                assert fan_specific_info.get("Lower Critical") is not None
                assert fan_specific_info.get("Lower Non_Critical") is not None
                assert fan_specific_info.get("Upper Non_Critical") is not None
                assert fan_specific_info.get("Upper Critical") is not None
                assert fan_specific_info.get("Upper Non_Recoverable") is not None
                assert fan_specific_info.get("Positive Hysteresis") is not None
                assert fan_specific_info.get("Negative Hysteresis") is not None
                assert fan_specific_info.get("Assertion Events") is not None
                assert fan_specific_info.get("Assertions Enabled") is not None
                assert fan_specific_info.get("Deassertions Enabled") is not None
    else:
        # Skip any validation if ERROR seen on the specifc FRU
        if not fan_specific_infos.get("ERROR"):
            assert fan_specific_infos.get("Sensor Type (Threshold)") is not None
            assert fan_specific_infos.get("Sensor Reading") is not None
            assert fan_specific_infos.get("Status") is not None
            assert fan_specific_infos.get("Lower Non_Recoverable") is not None
            assert fan_specific_infos.get("Lower Critical") is not None
            assert fan_specific_infos.get("Lower Non_Critical") is not None
            assert fan_specific_infos.get("Upper Non_Critical") is not None
            assert fan_specific_infos.get("Upper Critical") is not None
            assert fan_specific_infos.get("Upper Non_Recoverable") is not None
            assert fan_specific_infos.get("Positive Hysteresis") is not None
            assert fan_specific_infos.get("Negative Hysteresis") is not None
            assert fan_specific_infos.get("Assertion Events") is not None
            assert fan_specific_infos.get("Assertions Enabled") is not None
            assert fan_specific_infos.get("Deassertions Enabled") is not None
            assert fan_specific_infos.get("resource_id") is not None

def send_msg_request(resource_type, instance_id):
    request = {
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
            "actuator_request_type": {
                "node_controller": {
                    "node_request": resource_type,
                    "resource": instance_id
                }
            }
        }
    }
    write_to_egress_msgQ(request)

test_list = [test_node_fan_module_actuator]
