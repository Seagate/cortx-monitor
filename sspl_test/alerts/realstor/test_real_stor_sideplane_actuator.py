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
from common import check_sspl_ll_is_running


def init(args):
    pass

def test_real_stor_sideplane_module_actuator(agrs):
    check_sspl_ll_is_running()
    # sideplane_actuator_message_request("ENCL:enclosure:fru:sideplane", "Left Sideplane")
    sideplane_actuator_message_request("ENCL:enclosure:fru:sideplane", "*")
    sideplane_module_actuator_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:fru:sideplane":
                sideplane_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)
    assert(sideplane_module_actuator_msg is not None)
    assert(sideplane_module_actuator_msg.get("alert_type") is not None)
    assert(sideplane_module_actuator_msg.get("alert_id") is not None)
    assert(sideplane_module_actuator_msg.get("severity") is not None)
    assert(sideplane_module_actuator_msg.get("host_id") is not None)
    assert(sideplane_module_actuator_msg.get("info") is not None)

    sideplane_module_info = sideplane_module_actuator_msg.get("info")
    assert(sideplane_module_info.get("site_id") is not None)
    assert(sideplane_module_info.get("node_id") is not None)
    assert(sideplane_module_info.get("cluster_id") is not None)
    assert(sideplane_module_info.get("rack_id") is not None)
    assert(sideplane_module_info.get("resource_type") is not None)
    assert(sideplane_module_info.get("event_time") is not None)
    assert(sideplane_module_info.get("resource_id") is not None)

    sideplane_specific_info = sideplane_module_actuator_msg.get("specific_info", {})

    resource_id = sideplane_module_info.get("resource_id")
    if resource_id == "*":
        verify_sideplane_module_specific_info(sideplane_specific_info)
        return

    if sideplane_specific_info:
        assert (sideplane_specific_info.get("object_name") is not None)
        assert (sideplane_specific_info.get("durable_id") is not None)
        assert (sideplane_specific_info.get("status") is not None)
        assert (sideplane_specific_info.get("name") is not None)
        assert (sideplane_specific_info.get("enclosure_id") is not None)
        assert (sideplane_specific_info.get("drawer_id") is not None)
        assert (sideplane_specific_info.get("dom_id") is not None)
        assert (sideplane_specific_info.get("path_id") is not None)
        assert (sideplane_specific_info.get("path_id_numeric") is not None)
        assert (sideplane_specific_info.get("location") is not None)
        assert (sideplane_specific_info.get("position") is not None)
        assert (sideplane_specific_info.get("position_numeric") is not None)
        assert (sideplane_specific_info.get("status_numeric") is not None)
        assert (sideplane_specific_info.get("extended_status") is not None)
        assert (sideplane_specific_info.get("health") is not None)
        assert (sideplane_specific_info.get("health_numeric") is not None)
        assert (sideplane_specific_info.get("health_reason") is not None)
        assert (sideplane_specific_info.get("health_recommendation") is not None)

    expanders = sideplane_module_actuator_msg.get("specific_info").get("sideplanes", [])
    if expanders:
        for expander in expanders:
            assert (expander.get("object_name") is not None)
            assert (expander.get("durable_id") is not None)
            assert (expander.get("status") is not None)
            assert (expander.get("name") is not None)
            assert (expander.get("enclosure_id") is not None)
            assert (expander.get("drawer_id") is not None)
            assert (expander.get("dom_id") is not None)
            assert (expander.get("path_id") is not None)
            assert (expander.get("path_id_numeric") is not None)
            assert (expander.get("location") is not None)
            assert (expander.get("status_numeric") is not None)
            assert (expander.get("extended_status") is not None)
            assert (expander.get("fw_revision") is not None)
            assert (expander.get("health") is not None)
            assert (expander.get("health_numeric") is not None)
            assert (expander.get("health_reason") is not None)
            assert (expander.get("health_recommendation") is not None)

def verify_sideplane_module_specific_info(sideplane_specific_info):
    """Verify sideplane_module specific info"""

    if sideplane_specific_info:
        for fru_info in sideplane_specific_info:
            assert (fru_info.get("object_name") is not None)
            assert (fru_info.get("durable_id") is not None)
            assert (fru_info.get("status") is not None)
            assert (fru_info.get("name") is not None)
            assert (fru_info.get("enclosure_id") is not None)
            assert (fru_info.get("drawer_id") is not None)
            assert (fru_info.get("dom_id") is not None)
            assert (fru_info.get("path_id") is not None)
            assert (fru_info.get("path_id_numeric") is not None)
            assert (fru_info.get("location") is not None)
            assert (fru_info.get("position") is not None)
            assert (fru_info.get("position_numeric") is not None)
            assert (fru_info.get("status_numeric") is not None)
            assert (fru_info.get("extended_status") is not None)
            assert (fru_info.get("health") is not None)
            assert (fru_info.get("health_numeric") is not None)
            assert (fru_info.get("health_reason") is not None)
            assert (fru_info.get("health_recommendation") is not None)
            expanders = fru_info.get("expanders", [])
            if expanders:
                for expander in expanders:
                    assert(expander.get("object_name") is not None)
                    assert(expander.get("durable_id") is not None)
                    assert(expander.get("status") is not None)
                    assert(expander.get("name") is not None)
                    assert(expander.get("enclosure_id") is not None)
                    assert(expander.get("drawer_id") is not None)
                    assert(expander.get("dom_id") is not None)
                    assert(expander.get("path_id") is not None)
                    assert(expander.get("path_id_numeric") is not None)
                    assert(expander.get("location") is not None)
                    assert(expander.get("status_numeric") is not None)
                    assert(expander.get("extended_status") is not None)
                    assert(expander.get("fw_revision") is not None)
                    assert(expander.get("health") is not None)
                    assert(expander.get("health_numeric") is not None)
                    assert(expander.get("health_reason") is not None)
                    assert(expander.get("health_recommendation") is not None)

def sideplane_actuator_message_request(resource_type, resource_id):
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
            "request_path": {
                "site_id": "1",
                "rack_id": "1",
                "cluster_id": "1",
                "node_id": "1"
            },
            "response_dest": {},
            "actuator_request_type": {
                "storage_enclosure": {
                    "enclosure_request": resource_type,
                    "resource": resource_id
                }
            }
        }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_real_stor_sideplane_module_actuator]
