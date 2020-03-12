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

def test_node_psu_module_actuator(agrs):
    check_sspl_ll_is_running()
    psu_actuator_message_request("NDHW:node:fru:psu", "*")
    psu_module_actuator_msg = None
    time.sleep(10)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s " % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("actuator_response_type")
            if msg_type["info"]["resource_type"] == "node:fru:psu":
                psu_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(psu_module_actuator_msg is not None)
    assert(psu_module_actuator_msg.get("alert_type") is not None)
    assert(psu_module_actuator_msg.get("severity") is not None)
    assert(psu_module_actuator_msg.get("host_id") is not None)
    assert(psu_module_actuator_msg.get("info") is not None)
    assert(psu_module_actuator_msg.get("instance_id") is not None)

    psu_module_info = psu_module_actuator_msg.get("info")
    assert(psu_module_info.get("site_id") is not None)
    assert(psu_module_info.get("node_id") is not None)
    assert(psu_module_info.get("rack_id") is not None)
    assert(psu_module_info.get("resource_type") is not None)
    assert(psu_module_info.get("event_time") is not None)
    assert(psu_module_info.get("resource_id") is not None)

    fru_specific_infos = psu_module_actuator_msg.get("specific_info", {})

    if fru_specific_infos:
        for fru_specific_info in fru_specific_infos:
            resource_id = fru_specific_info.get("resource_id")
            if "PS1 psu Fail" in resource_id or "PS2 psu Fail" in resource_id:
                assert(fru_specific_info.get("Sensor Type (Discrete)") is not None)
                assert(fru_specific_info.get("resource_id") is not None)
            elif  "System psu" in resource_id:
                assert(fru_specific_info.get("Status") is not None)
                assert(fru_specific_info.get("Sensor Type (Threshold)") is not None)
                assert(fru_specific_info.get("Sensor Reading") is not None)
                assert(fru_specific_info.get("Lower Non-Recoverable") is not None)
                assert(fru_specific_info.get("Assertions Enabled") is not None)
                assert(fru_specific_info.get("Upper Non-Critical") is not None)
                assert(fru_specific_info.get("Upper Non-Recoverable") is not None)
                assert(fru_specific_info.get("Positive Hysteresis") is not None)
                assert(fru_specific_info.get("Lower Critical") is not None)
                assert(fru_specific_info.get("Deassertions Enabled") is not None)
                assert(fru_specific_info.get("Lower Non-Critical") is not None)
                assert(fru_specific_info.get("Upper Critical") is not None)
                assert(fru_specific_info.get("Negative Hysteresis") is not None)
                assert(fru_specific_info.get("Assertion Events") is not None)
                assert(fru_specific_info.get("resource_id") is not None)
            else:
                assert(fru_specific_info.get("States Asserted") is not None)
                assert(fru_specific_info.get("Sensor Type (Discrete)") is not None)
                assert(fru_specific_info.get("resource_id") is not None)

def psu_actuator_message_request(resource_type, resource_id):
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
				"resource": resource_id
			}
		}
	}
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_node_psu_module_actuator]

