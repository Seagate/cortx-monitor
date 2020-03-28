# -*- coding: utf-8 -*-
import json
import os
import time
import sys

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from sspl_test.common import check_sspl_ll_is_running

def init(args):
    pass

def test_node_disk_module_actuator(agrs):
    print("Enters into test_node_disk_module_actuator")
    check_sspl_ll_is_running()
    disk_actuator_message_request("NDHW:node:fru:disk")
    disk_actuator_msg = None
    time.sleep(10)
    for i in range(5):
        while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
            ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
            time.sleep(0.0001)
            print("Received: %s " % ingressMsg)
            try:
                # Make sure we get back the message type that matches the request
                msg_type = ingressMsg.get("actuator_response_type")
                if msg_type["info"]["resource_type"] == "node:fru:disk":
                    disk_actuator_msg = msg_type
                    break
            except Exception as exception:
                time.sleep(0.0001)
                print(exception)

        if disk_actuator_msg:
            break
        time.sleep(2)

    assert(disk_actuator_msg is not None)
    assert(disk_actuator_msg.get("alert_type") is not None)
    # assert(disk_actuator_msg.get("alert_id") is not None)
    assert(disk_actuator_msg.get("severity") is not None)
    assert(disk_actuator_msg.get("host_id") is not None)
    assert(disk_actuator_msg.get("info") is not None)

    disk_actuator_info = disk_actuator_msg.get("info")
    assert(disk_actuator_info.get("site_id") is not None)
    assert(disk_actuator_info.get("node_id") is not None)
    # assert(disk_actuator_info.get("cluster_id") is not None)
    assert(disk_actuator_info.get("rack_id") is not None)
    assert(disk_actuator_info.get("resource_type") is not None)
    assert(disk_actuator_info.get("event_time") is not None)
    assert(disk_actuator_info.get("resource_id") is not None)

    disk_actuator_specific_infos = disk_actuator_msg.get("specific_info")
    for disk_actuator_specific_info in disk_actuator_specific_infos:
        assert(disk_actuator_specific_info is not None)
        assert(disk_actuator_specific_info.get("Sensor Type (Discrete)") is not None)
        assert(disk_actuator_specific_info.get("resource_id") is not None)
        if "States Asserted" in disk_actuator_specific_info:
            assert(disk_actuator_specific_info.get("States Asserted") is not None)

def disk_actuator_message_request(resource_type):
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
				"resource": "*"
			}
		}
	}
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_node_disk_module_actuator]
