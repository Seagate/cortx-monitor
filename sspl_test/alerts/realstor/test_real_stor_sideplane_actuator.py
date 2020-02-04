# -*- coding: utf-8 -*-
import json
import os
import psutil
import time
import sys

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from sspl_test.common import check_sspl_ll_is_running

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
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:fru:sideplane":
                sideplane_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
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
        assert (sideplane_specific_info.get("object-name") is not None)
        assert (sideplane_specific_info.get("durable-id") is not None)
        assert (sideplane_specific_info.get("status") is not None)
        assert (sideplane_specific_info.get("name") is not None)
        assert (sideplane_specific_info.get("enclosure-id") is not None)
        assert (sideplane_specific_info.get("drawer-id") is not None)
        assert (sideplane_specific_info.get("dom-id") is not None)
        assert (sideplane_specific_info.get("path-id") is not None)
        assert (sideplane_specific_info.get("path-id-numeric") is not None)
        assert (sideplane_specific_info.get("location") is not None)
        assert (sideplane_specific_info.get("position") is not None)
        assert (sideplane_specific_info.get("position-numeric") is not None)
        assert (sideplane_specific_info.get("status-numeric") is not None)
        assert (sideplane_specific_info.get("extended-status") is not None)
        assert (sideplane_specific_info.get("health") is not None)
        assert (sideplane_specific_info.get("health-numeric") is not None)
        assert (sideplane_specific_info.get("health-reason") is not None)
        assert (sideplane_specific_info.get("health-recommendation") is not None)

    expanders = sideplane_module_actuator_msg.get("specific_info").get("sideplanes", [])
    if expanders:
        for expander in expanders:
            assert (expander.get("object-name") is not None)
            assert (expander.get("durable-id") is not None)
            assert (expander.get("status") is not None)
            assert (expander.get("name") is not None)
            assert (expander.get("enclosure-id") is not None)
            assert (expander.get("drawer-id") is not None)
            assert (expander.get("dom-id") is not None)
            assert (expander.get("path-id") is not None)
            assert (expander.get("path-id-numeric") is not None)
            assert (expander.get("location") is not None)
            assert (expander.get("status-numeric") is not None)
            assert (expander.get("extended-status") is not None)
            assert (expander.get("fw-revision") is not None)
            assert (expander.get("health") is not None)
            assert (expander.get("health-numeric") is not None)
            assert (expander.get("health-reason") is not None)
            assert (expander.get("health-recommendation") is not None)

def verify_sideplane_module_specific_info(sideplane_specific_info):
    """Verify sideplane_module specific info"""

    if sideplane_specific_info:
        for fru_info in sideplane_specific_info:
            assert (fru_info.get("object-name") is not None)
            assert (fru_info.get("durable-id") is not None)
            assert (fru_info.get("status") is not None)
            assert (fru_info.get("name") is not None)
            assert (fru_info.get("enclosure-id") is not None)
            assert (fru_info.get("drawer-id") is not None)
            assert (fru_info.get("dom-id") is not None)
            assert (fru_info.get("path-id") is not None)
            assert (fru_info.get("path-id-numeric") is not None)
            assert (fru_info.get("location") is not None)
            assert (fru_info.get("position") is not None)
            assert (fru_info.get("position-numeric") is not None)
            assert (fru_info.get("status-numeric") is not None)
            assert (fru_info.get("extended-status") is not None)
            assert (fru_info.get("health") is not None)
            assert (fru_info.get("health-numeric") is not None)
            assert (fru_info.get("health-reason") is not None)
            assert (fru_info.get("health-recommendation") is not None)
            expanders = fru_info.get("expanders", [])
            if expanders:
                for expander in expanders:
                    assert(expander.get("object-name") is not None)
                    assert(expander.get("durable-id") is not None)
                    assert(expander.get("status") is not None)
                    assert(expander.get("name") is not None)
                    assert(expander.get("enclosure-id") is not None)
                    assert(expander.get("drawer-id") is not None)
                    assert(expander.get("dom-id") is not None)
                    assert(expander.get("path-id") is not None)
                    assert(expander.get("path-id-numeric") is not None)
                    assert(expander.get("location") is not None)
                    assert(expander.get("status-numeric") is not None)
                    assert(expander.get("extended-status") is not None)
                    assert(expander.get("fw-revision") is not None)
                    assert(expander.get("health") is not None)
                    assert(expander.get("health-numeric") is not None)
                    assert(expander.get("health-reason") is not None)
                    assert(expander.get("health-recommendation") is not None)

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
                "site_id": 1,
                "rack_id": 1,
                "cluster_id": 1,
                "node_id": 1
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
