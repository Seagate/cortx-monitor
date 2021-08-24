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
import subprocess

from default import world
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests
from common import check_sspl_ll_is_running, send_enclosure_sensor_request


def init(args):
    pass

def test_real_stor_enclosure_sensor(args):
    timeout = time.time() + 60*3
    check_sspl_ll_is_running()
    kill_mock_server()
    instance_id = "*"
    resource_type = "storage"
    ingress_msg_type = "sensor_response_type"
    send_enclosure_sensor_request(resource_type, instance_id)
    encl_sensor_msg = None
    while time.time() < timeout:
        if world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
            time.sleep(1)
            continue
        ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get(ingress_msg_type)
            if msg_type["info"]["resource_type"] == resource_type:
                encl_sensor_msg = ingressMsg.get(ingress_msg_type)
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)
        if encl_sensor_msg:
            break

    assert(encl_sensor_msg is not None), "Timeout error, Real Store Enclosure Sensor test is failed."
    assert(encl_sensor_msg.get("alert_type") is not None)
    assert(encl_sensor_msg.get("alert_id") is not None)
    assert(encl_sensor_msg.get("severity") is not None)
    assert(encl_sensor_msg.get("host_id") is not None)
    assert(encl_sensor_msg.get("info") is not None)

    encl_sensor_info = encl_sensor_msg.get("info")
    assert(encl_sensor_info.get("site_id") is not None)
    assert(encl_sensor_info.get("rack_id") is not None)
    assert(encl_sensor_info.get("node_id") is not None)
    assert(encl_sensor_info.get("cluster_id") is not None)
    assert(encl_sensor_info.get("resource_id") is not None)
    assert(encl_sensor_info.get("resource_type") is not None)
    assert(encl_sensor_info.get("event_time") is not None)
    assert(encl_sensor_info.get("description") is not None)

    encl_specific_info = encl_sensor_msg.get("specific_info")
    if encl_specific_info:
        assert(encl_specific_info.get("event") is not None)

def kill_mock_server():
    cmd = "sudo pkill -f mock_server"
    result = run_cmd(cmd)
    if result:
        time.sleep(90)

def run_cmd(cmd):
    process = subprocess.run(cmd, shell=True)
    if process.returncode !=0:
        res = False
    res = True
    return res

test_list = [test_real_stor_enclosure_sensor]
