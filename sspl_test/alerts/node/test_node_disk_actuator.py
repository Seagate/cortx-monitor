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


UUID="16476007-a739-4785-b5c6-f3de189cdf18"

def init(args):
    pass

def test_node_disk_module_actuator(agrs):
    check_sspl_ll_is_running()
    instance_id = "*"
    resource_type = "node:fru:disk"
    send_msg_request("NDHW:%s" % resource_type, instance_id)
    ingressMsg = get_fru_response(resource_type, instance_id)

    assert(ingressMsg.get("sspl_ll_msg_header").get("uuid") == UUID)

    disk_actuator_msg = ingressMsg.get("actuator_response_type")
    assert(disk_actuator_msg is not None)
    assert(disk_actuator_msg.get("alert_type") is not None)
    assert(disk_actuator_msg.get("severity") is not None)
    assert(disk_actuator_msg.get("host_id") is not None)
    assert(disk_actuator_msg.get("info") is not None)
    assert(disk_actuator_msg.get("instance_id") == instance_id)

    disk_actuator_info = disk_actuator_msg.get("info")
    assert(disk_actuator_info.get("site_id") is not None)
    assert(disk_actuator_info.get("node_id") is not None)
    assert(disk_actuator_info.get("rack_id") is not None)
    assert(disk_actuator_info.get("resource_type") is not None)
    assert(disk_actuator_info.get("event_time") is not None)
    assert(disk_actuator_info.get("resource_id") is not None)

    disk_specific_infos = disk_actuator_msg.get("specific_info")
    assert(disk_specific_infos is not None)

    if disk_actuator_info.get("resource_id") == "*":
        for disk_specific_info in disk_specific_infos:
            assert(disk_specific_info is not None)
            if disk_specific_info.get("ERROR"):
                # Skip any validation on specific info if ERROR seen on FRU
                continue
            resource_id = disk_specific_info.get("resource_id", "")
            if disk_specific_info.get(resource_id):
                assert(disk_specific_info.get(resource_id).get("ERROR") is not None)
                # Skip any validation on specific info if ERROR seen on sensor
                continue
            sensor_type = [
                k if k.startswith("Sensor Type") else None
                for k in disk_specific_info.keys()
                ][0]
            assert(sensor_type is not None)
            assert(disk_specific_info.get("resource_id") is not None)
            if "States Asserted" in disk_specific_info:
                assert(disk_specific_info.get("States Asserted") is not None)
    else:
        # Skip any validation if ERROR seen on the specifc FRU
        if not disk_specific_infos.get("ERROR"):
            sensor_type = [
                k if k.startswith("Sensor Type") else None
                for k in disk_specific_infos.keys()
                ][0]
            assert(sensor_type is not None)
            assert(disk_specific_infos.get("resource_id") is not None)
            if "States Asserted" in disk_specific_infos:
                assert(disk_specific_infos.get("States Asserted") is not None)

def send_msg_request(resource_type, instance_id):
    request = {
	"username": "sspl-ll",
	"expires": 3600,
	"description": "Seagate Storage Platform Library - Actuator Request",
	"title": "SSPL-LL Actuator Request",
	"signature": "None",
	"time": "2018-07-31 04:08:04.071170",
	"message": {
		"sspl_ll_msg_header": {
			"msg_version": "1.0.0",
			"uuid": UUID,
			"schema_version": "1.0.0",
			"sspl_version": "1.0.0"
		},
		"sspl_ll_debug": {
			"debug_component": "sensor",
			"debug_enabled": True
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

test_list = [test_node_disk_module_actuator]
