# -*- coding: utf-8 -*-
import json
import os
import psutil
import time
import sys
import subprocess

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from sspl_test.common import check_sspl_ll_is_running

def init(args):
    pass

def test_real_stor_enclosure_sensor(agrs):
    timeout = time.time() + 60*3
    check_sspl_ll_is_running()
    kill_mock_server()
    encl_sensor_message_request("enclosure")
    encl_sensor_msg = None
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure":
                encl_sensor_msg = ingressMsg.get("sensor_response_type")
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)
        if time.time() > timeout:
            print("Timeout Error, Test Failed")
            break

    assert(encl_sensor_msg is not None)
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

    encl_specific_info = encl_sensor_msg.get("specific_info")
    if encl_specific_info:
        assert(encl_specific_info.get("event") is not None)

def kill_mock_server():
    running_process = []
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

def encl_sensor_message_request(resource_type):
    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "1576148751",
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
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_real_stor_enclosure_sensor]
