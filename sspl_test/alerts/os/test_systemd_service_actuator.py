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

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from sspl_test.common import check_sspl_ll_is_running

def init(args):
    pass

def test_systemd_service_valid_request(args):
    check_sspl_ll_is_running()
    # TODO: Change service name, once get final 3rd party service name
    service_actuator_request("rabbitmq-server.service", "status")
    service_actuator_msg = None
    time.sleep(6)
    ingressMsg = {}
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s " % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "node:sw:os:service":
                service_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)

    assert(service_actuator_msg is not None)
    assert(service_actuator_msg.get("alert_type") is not None)
    assert(service_actuator_msg.get("severity") is not None)
    assert(service_actuator_msg.get("host_id") is not None)
    assert(service_actuator_msg.get("info") is not None)
    
    info = service_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    assert(service_actuator_msg.get("specific_info") is not None)

def test_systemd_service_invalid_request(args):
    check_sspl_ll_is_running()
    service_actuator_request("temp_dummpy.service", "status")
    service_actuator_msg = None
    time.sleep(6)
    ingressMsg = {}
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s " % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "node:sw:os:service":
                service_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)

    assert(service_actuator_msg is not None)
    assert(service_actuator_msg.get("alert_type") is not None)
    assert(service_actuator_msg.get("severity") is not None)
    assert(service_actuator_msg.get("host_id") is not None)
    assert(service_actuator_msg.get("info") is not None)
    
    info = service_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    assert(service_actuator_msg.get("specific_info") is not None)
    specific_info = service_actuator_msg.get("specific_info")
    assert (specific_info[0].get("error_msg") is not None)

def service_actuator_request(service_name, action):
    egressMsg = {
                "title": "SSPL-LL Actuator Request",
                "description": "Seagate Storage Platform Library - Actuator Request",
                "username": "sspl-ll",
                "expires": 3600,
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
                        "sspl_version": "2.0.0"
                    },
                    "request_path": {
                        "site_id": "1",
                        "rack_id": "1",
                        "node_id": "1"
                    },
                    "response_dest": {},
                        "actuator_request_type": {
                            "service_controller": {
                                "service_request": action,
                                "service_name": service_name
                                
                            }
                    }
                }
            }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)
    
test_list = [test_systemd_service_valid_request, test_systemd_service_invalid_request]
