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

from default import world
from rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from common import check_sspl_ll_is_running
from cortx.utils.service import DbusServiceHandler
from alerts.os.dummy_service_files import simulate_service_alerts

RESOURCE_TYPE = "node:sw:os:service"
WAIT_TIME = 50   # 30s wait_time (set for testing) + 20s buffer
service_name = "dummy_service.service"

def init(args):
    pass

def check_service_is_running(service_name):
    state = DbusServiceHandler().get_state(service_name).state
    assert(state == "active")
    return state

def assert_on_mismatch(sensor_response, alert_type):
    assert(sensor_response is not None)
    assert(sensor_response.get("alert_type") == alert_type)
    assert(sensor_response.get("severity") is not None)
    assert(sensor_response.get("host_id") is not None)
    assert(sensor_response.get("info") is not None)

    info = sensor_response.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") == RESOURCE_TYPE)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") == service_name)

    assert(sensor_response.get("specific_info") is not None)
    specific_info = sensor_response.get("specific_info")
    assert (specific_info.get("state") is not None)
    assert (specific_info.get("previous_state") is not None)
    assert (specific_info.get("substate") is not None)
    assert (specific_info.get("previous_substate") is not None)
    assert (specific_info.get("pid") is not None)
    assert (specific_info.get("previous_pid") is not None)

def read_ingress_queue():
    """Read ingress queue and extract msg with matching RESOURCE_TYPE."""
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]\
                                                    ._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]\
                                                    ._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s " % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == RESOURCE_TYPE:
                return msg_type
        except Exception as exception:
            time.sleep(0.1)
            print(exception)
    return None

def test_service_inactive_alert(args):
    check_sspl_ll_is_running()
    check_service_is_running(service_name)
    # Simulate Fault alert by stopping the service.
    DbusServiceHandler().stop(service_name)
    time.sleep(WAIT_TIME)
    sensor_response = read_ingress_queue()
    assert_on_mismatch(sensor_response, "fault")
    # Simulate Fault resolved alert.
    DbusServiceHandler().start(service_name)
    time.sleep(5)
    sensor_response = read_ingress_queue()
    assert_on_mismatch(sensor_response, "fault_resolved")

def test_service_failed_alert(args):
    check_sspl_ll_is_running()
    check_service_is_running(service_name)
    simulate_service_alerts.simulate_fault_alert()
    time.sleep(5)
    sensor_response = read_ingress_queue()
    assert_on_mismatch(sensor_response, "fault")
    simulate_service_alerts.restore_service_file()
    time.sleep(5)
    sensor_response = read_ingress_queue()
    assert_on_mismatch(sensor_response, "fault_resolved")

def test_service_restart_case(args):
    check_sspl_ll_is_running()
    check_service_is_running(service_name)
    DbusServiceHandler().restart(service_name)
    time.sleep(WAIT_TIME)
    sensor_response = read_ingress_queue()
    check_service_is_running(service_name)
    if sensor_response:
        print(sensor_response)
        assert(sensor_response['info']['alert_type'] != "fault")
    simulate_service_alerts.cleanup()

test_list = [test_service_inactive_alert,
             test_service_failed_alert,
             test_service_restart_case]
