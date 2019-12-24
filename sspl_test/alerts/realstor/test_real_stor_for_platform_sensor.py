import json
import os
import psutil
import time
import sys

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

def init(args):
    pass

def test_real_stor_sensor_current(agrs):
    check_sspl_ll_is_running()
    enclosure_sensor_message_request("ENCL:enclosure:sensor:current", "*")
    enclosure_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:sensor:current":
                current_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print exception

    assert(current_module_actuator_msg is not None)
    assert(current_module_actuator_msg.get("alert_type") is not None)
    assert(current_module_actuator_msg.get("alert_id") is not None)
    assert(current_module_actuator_msg.get("severity") is not None)
    assert(current_module_actuator_msg.get("host_id") is not None)
    assert(current_module_actuator_msg.get("info") is not None)
    assert(current_module_actuator_msg.get("specific_info") is not None)

    info = current_module_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = current_module_actuator_msg.get("specific_info")
    generic_specific_info(specific_info)


def test_real_stor_sensor_voltage(agrs):
    check_sspl_ll_is_running()
    enclosure_sensor_message_request("ENCL:enclosure:sensor:voltage", "*")
    enclosure_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:sensor:voltage":
                voltage_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print exception

    assert(voltage_module_actuator_msg is not None)
    assert(voltage_module_actuator_msg.get("alert_type") is not None)
    assert(voltage_module_actuator_msg.get("alert_id") is not None)
    assert(voltage_module_actuator_msg.get("severity") is not None)
    assert(voltage_module_actuator_msg.get("host_id") is not None)
    assert(voltage_module_actuator_msg.get("info") is not None)
    assert(voltage_module_actuator_msg.get("specific_info") is not None)

    info = voltage_module_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = voltage_module_actuator_msg.get("specific_info")
    generic_specific_info(specific_info)


def test_real_stor_sensor_temperature(agrs):
    check_sspl_ll_is_running()
    enclosure_sensor_message_request("ENCL:enclosure:sensor:temperature", "*")
    enclosure_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:sensor:temperature":
                temperature_module_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print exception

    assert(temperature_module_actuator_msg is not None)
    assert(temperature_module_actuator_msg.get("alert_type") is not None)
    assert(temperature_module_actuator_msg.get("alert_id") is not None)
    assert(temperature_module_actuator_msg.get("severity") is not None)
    assert(temperature_module_actuator_msg.get("host_id") is not None)
    assert(temperature_module_actuator_msg.get("info") is not None)
    assert(temperature_module_actuator_msg.get("specific_info") is not None)

    info = temperature_module_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = temperature_module_actuator_msg.get("specific_info")
    generic_specific_info(specific_info)


def generic_specific_info(specific_info):
    for resource in specific_info:
        assert(resource.get("drawer-id-numeric") is not None)
        assert(resource.get("sensor-type") is not None)
        assert(resource.get("container") is not None)
        assert(resource.get("enclosure-id") is not None)
        assert(resource.get("durable-id") is not None)
        assert(resource.get("value") is not None)
        assert(resource.get("status") is not None)
        assert(resource.get("controller-id-numeric") is not None)
        assert(resource.get("object-name") is not None)
        assert(resource.get("container-numeric") is not None)
        assert(resource.get("controller-id") is not None)
        assert(resource.get("sensor-type-numeric") is not None)
        assert(resource.get("sensor-name") is not None)
        assert(resource.get("drawer-id") is not None)
        assert(resource.get("status-numeric") is not None)

def check_sspl_ll_is_running():
    # Check that the state for sspl service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspl_ll_d" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['cmdline', 'status'])
            if "sspl_ll_d" in str(pinfo['cmdline']) and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

def enclosure_sensor_message_request(resource_type, resource_id):

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

test_list = [test_real_stor_sensor_current, test_real_stor_sensor_voltage, test_real_stor_sensor_temperature]