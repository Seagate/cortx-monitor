# -*- coding: utf-8 -*-
from lettuce import *

import json
import os
import psutil
import time

# Add the top level directory to the sys.path to access classes
topdir = os.path.dirname(os.path.dirname(os.path.dirname \
            (os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, topdir)

from test.automated.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

@step(u'Given that SSPL is running')
def given_that_sspl_ll_is_running(step):
    # Check that the state for sspl_ll service is active
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


@step(u'When I send in the enclosure actuator message to request the current "([^"]*)" data with instance id "([^"]*)"')
def when_i_send_in_the_enclosure_actuator_message_to_request_the_current_fru_type_data(step, resource_type, resource_id):
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

@step(u'Then I get the fan module JSON response message')
def then_i_get_the_fan_module_json_response_message(step):

    fan_module_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: {0}".format(ingressMsg))
        try:
            # Make sure we get back the message type that matches the request
            fan_module_sensor_msg = ingressMsg.get("sensor_response_type")
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(fan_module_sensor_msg is not None)
    assert(fan_module_sensor_msg.get("alert_type") is not None)
    assert(fan_module_sensor_msg.get("alert_id") is not None)
    assert(fan_module_sensor_msg.get("severity") is not None)
    assert(fan_module_sensor_msg.get("host_id") is not None)
    assert(fan_module_sensor_msg.get("info") is not None)

    fan_module_info = fan_module_sensor_msg.get("info")
    assert(fan_module_info.get("site_id") is not None)
    assert(fan_module_info.get("node_id") is not None)
    assert(fan_module_info.get("cluster_id") is not None)
    assert(fan_module_info.get("rack_id") is not None)
    assert(fan_module_info.get("resource_type") is not None)
    assert(fan_module_info.get("event_time") is not None)
    assert(fan_module_info.get("resource_id") is not None)

    fru_specific_info = fan_module_sensor_msg.get("specific_info", {})

    resource_id = fan_module_info.get("resource_id")
    if resource_id == "*":
        verify_fan_module_specific_info(fru_specific_info)
        return

    if fru_specific_info:
        assert(fru_specific_info.get("durable-id") is not None)
        assert(fru_specific_info.get("status") is not None)
        assert(fru_specific_info.get("name") is not None)
        assert(fru_specific_info.get("enclosure-id") is not None)
        assert(fru_specific_info.get("health") is not None)
        assert(fru_specific_info.get("health-reason") is not None)
        assert(fru_specific_info.get("location") is not None)
        assert(fru_specific_info.get("health-recommendation") is not None)
        assert(fru_specific_info.get("position") is not None)

    fans = fan_module_sensor_msg.get("specific_info").get("fans", [])
    if fans:
        for fan in fans:
            assert(fan.get("durable-id") is not None)
            assert(fan.get("status") is not None)
            assert(fan.get("name") is not None)
            assert(fan.get("speed") is not None)
            assert(fan.get("locator-led") is not None)
            assert(fan.get("position") is not None)
            assert(fan.get("location") is not None)
            assert(fan.get("part-number") is not None)
            assert(fan.get("serial-number") is not None)
            assert(fan.get("fw-revision") is not None)
            assert(fan.get("hw-revision") is not None)
            assert(fan.get("health") is not None)
            assert(fan.get("health-reason") is not None)
            assert(fan.get("health-recommendation") is not None)

@step(u'Then I get the disk actuator JSON response message for disk instance "([^"]*)"')
def then_i_get_the_disk_actuator_json_response_message(step, resource_id):

    disk_actuator_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            time.sleep(2)
            if msg_type['info']['resource_type'] == "enclosure:fru:disk":
                disk_actuator_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print exception

    assert(disk_actuator_msg is not None)
    assert(disk_actuator_msg.get("alert_type") is not None)
    assert(disk_actuator_msg.get("severity") is not None)
    assert(disk_actuator_msg.get("alert_id") is not None)
    assert(disk_actuator_msg.get("host_id") is not None)
    assert(disk_actuator_msg.get("info") is not None)

    disk_actuator_info = disk_actuator_msg.get("info")
    assert(disk_actuator_info.get("site_id") is not None)
    assert(disk_actuator_info.get("node_id") is not None)
    assert(disk_actuator_info.get("cluster_id") is not None)
    assert(disk_actuator_info.get("rack_id") is not None)
    assert(disk_actuator_info.get("resource_type") is not None)
    assert(disk_actuator_info.get("event_time") is not None)

    assert(disk_actuator_info.get("resource_id") is not None)
    if resource_id != "*":
        diskId = "disk_00.{}".format(resource_id)
        assert(disk_actuator_info.get("resource_id") == diskId)
    else:
        assert(disk_actuator_info.get("resource_id") == "*")

    disk_actuator_specific_info_array = disk_actuator_msg.get("specific_info")
    assert(disk_actuator_specific_info_array is not None)

    assert(len(disk_actuator_specific_info_array) > 0)
    if resource_id != "*":
        assert(len(disk_actuator_specific_info_array) == 1)
    else:
        assert(len(disk_actuator_specific_info_array) > 1)


    for disk_actuator_specific_info in disk_actuator_specific_info_array:
        assert(disk_actuator_specific_info is not None)
        assert(disk_actuator_specific_info.get("durable-id") is not None)
        if resource_id != "*":
            assert(disk_actuator_specific_info.get("durable-id") == diskId)
        assert(disk_actuator_specific_info.get("description") is not None)
        assert(disk_actuator_specific_info.get("slot") is not None)
        assert(disk_actuator_specific_info.get("status") is not None)
        assert(disk_actuator_specific_info.get("architecture") is not None)
        assert(disk_actuator_specific_info.get("serial-number") is not None)
        assert(disk_actuator_specific_info.get("size") is not None)
        assert(disk_actuator_specific_info.get("vendor") is not None)
        assert(disk_actuator_specific_info.get("model") is not None)
        assert(disk_actuator_specific_info.get("revision") is not None)
        assert(disk_actuator_specific_info.get("temperature") is not None)
        assert(disk_actuator_specific_info.get("led-status") is not None)
        assert(disk_actuator_specific_info.get("locator-led") is not None)
        assert(disk_actuator_specific_info.get("blink") is not None)
        assert(disk_actuator_specific_info.get("smart") is not None)
        assert(disk_actuator_specific_info.get("health") is not None)
        assert(disk_actuator_specific_info.get("health-reason") is not None)
        assert(disk_actuator_specific_info.get("health-recommendation") is not None)
        assert(disk_actuator_specific_info.get("enclosure-id") is not None)
        assert(disk_actuator_specific_info.get("enclosure-wwn") is not None)

@step(u'Then I get the controller JSON response message')
def then_i_get_the_controller_json_response_message(step):

    controller_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            controller_sensor_msg = ingressMsg.get("sensor_response_type")
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(controller_sensor_msg is not None)
    assert(controller_sensor_msg.get("alert_type") is not None)
    assert(controller_sensor_msg.get("alert_id") is not None)
    assert(controller_sensor_msg.get("severity") is not None)
    assert(controller_sensor_msg.get("host_id") is not None)
    assert(controller_sensor_msg.get("info") is not None)
    assert(controller_sensor_msg.get("specific_info") is not None)

    info = controller_sensor_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = controller_sensor_msg.get("specific_info")
    assert(specific_info.get("object-name") is not None)
    assert(specific_info.get("controller-id") is not None)
    assert(specific_info.get("serial-number") is not None)
    assert(specific_info.get("hardware-version") is not None)
    assert(specific_info.get("cpld-version") is not None)
    assert(specific_info.get("mac-address") is not None)
    assert(specific_info.get("node-wwn") is not None)
    assert(specific_info.get("ip-address") is not None)
    assert(specific_info.get("ip-subnet-mask") is not None)
    assert(specific_info.get("ip-gateway") is not None)
    assert(specific_info.get("disks") is not None)
    assert(specific_info.get("number-of-storage-pools") is not None)
    assert(specific_info.get("virtual-disks") is not None)
    assert(specific_info.get("host-ports") is not None)
    assert(specific_info.get("drive-channels") is not None)
    assert(specific_info.get("drive-bus-type") is not None)
    assert(specific_info.get("status") is not None)
    assert(specific_info.get("failed-over") is not None)
    assert(specific_info.get("fail-over-reason") is not None)
    assert(specific_info.get("vendor") is not None)
    assert(specific_info.get("model") is not None)
    assert(specific_info.get("platform-type") is not None)
    assert(specific_info.get("write-policy") is not None)
    assert(specific_info.get("description") is not None)
    assert(specific_info.get("part-number") is not None)
    assert(specific_info.get("revision") is not None)
    assert(specific_info.get("mfg-vendor-id") is not None)
    assert(specific_info.get("locator-led") is not None)
    assert(specific_info.get("health") is not None)
    assert(specific_info.get("health-reason") is not None)
    assert(specific_info.get("position") is not None)
    assert(specific_info.get("redundancy-mode") is not None)
    assert(specific_info.get("redundancy-status") is not None)
    assert(specific_info.get("compact-flash") is not None)
    assert(specific_info.get("network-parameters") is not None)
    assert(specific_info.get("expander-ports") is not None)
    assert(specific_info.get("expanders") is not None)
    assert(specific_info.get("port") is not None)

@step(u'When I send in the enclosure actuator request to get the current "([^"]*)" data for "([^"]*)" sensor')
def when_i_send_in_the_enclosure_actuator_message_to_request_the_current_sensor_type_data(step, resource_type, resource_id):
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
            "response_dest": {},
            "sspl_ll_msg_header": {
            "msg_version": "1.0.0",
            "uuid": "16476007-a739-4785-b5c7-f3de189cdf9d",
            "schema_version": "1.0.0",
            "sspl_version": "1.0.0"
            },
            "request_path": {
                "site_id": 0,
                "node_id": 1,
                "rack_id": 0,
                "cluster_id": 1
            },
            "actuator_request_type": {
                "storage_enclosure": {
                    "enclosure_request": resource_type,
                    "resource": resource_id
                }
            }
        }
        }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

@step(u'Then I get the sensor JSON response message for "([^"]*)" "([^"]*)" sensor')
def then_i_get_the_sensor_json_response_message(step, resource_id, sensor_type):

    storage_enclosure_sensor_actuator_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: {0}".format(ingressMsg))
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:sensor:{}".format(sensor_type.lower()):
                storage_enclosure_sensor_actuator_msg = msg_type
                break

        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(storage_enclosure_sensor_actuator_msg is not None)
    assert(storage_enclosure_sensor_actuator_msg.get("host_id") is not None)
    assert(storage_enclosure_sensor_actuator_msg.get("alert_type") is not None)
    assert(storage_enclosure_sensor_actuator_msg.get("alert_id") is not None)
    assert(storage_enclosure_sensor_actuator_msg.get("severity") is not None)

    sensor_info = storage_enclosure_sensor_actuator_msg.get("info")
    assert(sensor_info is not None)
    assert(sensor_info.get("site_id") is not None)
    assert(sensor_info.get("cluster_id") is not None)
    assert(sensor_info.get("rack_id") is not None)
    assert(sensor_info.get("node_id") is not None)
    assert(sensor_info.get("resource_type") is not None)
    assert((sensor_info.get("resource_id") == resource_id) is True)
    assert(sensor_info.get("event_time") is not None)

    sensor_specific_info = storage_enclosure_sensor_actuator_msg.get("specific_info")
    assert(sensor_specific_info is not None)

    if resource_id == "*":
        assert(isinstance(sensor_specific_info, list))
        for specific_info in sensor_specific_info:
            verify_specific_info_for_platform_sensors(specific_info, sensor_type)
    else:
        assert(isinstance(sensor_specific_info, dict))
        assert((sensor_specific_info.get("sensor-name") == resource_id) is True)
        verify_specific_info_for_platform_sensors(sensor_specific_info, sensor_type)

def verify_specific_info_for_platform_sensors(specific_info, sensor_type):
    assert(specific_info.get("drawer-id-numeric") is not None)
    assert(specific_info.get("status") is not None)
    assert(specific_info.get("container") is not None)
    assert(specific_info.get("enclosure-id") is not None)
    assert((specific_info.get("sensor-type") == sensor_type) is True)
    assert(specific_info.get("durable-id") is not None)
    assert(specific_info.get("value") is not None)
    assert(specific_info.get("object-name") is not None)
    assert(specific_info.get("controller-id-numeric") is not None)
    assert(specific_info.get("container-numeric") is not None)
    assert(specific_info.get("controller-id") is not None)
    assert(specific_info.get("sensor-type-numeric") is not None)
    assert(specific_info.get("drawer-id") is not None)
    assert(specific_info.get("status-numeric") is not None)

def verify_fan_module_specific_info(fru_specific_info):
    """Verify fan_module specific info"""

    if fru_specific_info:
        for fru_info in fru_specific_info:
            assert(fru_info.get("durable-id") is not None)
            assert(fru_info.get("status") is not None)
            assert(fru_info.get("name") is not None)
            assert(fru_info.get("enclosure-id") is not None)
            assert(fru_info.get("health") is not None)
            assert(fru_info.get("health-reason") is not None)
            assert(fru_info.get("location") is not None)
            assert(fru_info.get("health-recommendation") is not None)
            assert(fru_info.get("position") is not None)

            fans = fru_info.get("fans", [])
            if fans:
                for fan in fans:
                    assert(fan.get("durable-id") is not None)
                    assert(fan.get("status") is not None)
                    assert(fan.get("name") is not None)
                    assert(fan.get("speed") is not None)
                    assert(fan.get("locator-led") is not None)
                    assert(fan.get("position") is not None)
                    assert(fan.get("location") is not None)
                    assert(fan.get("part-number") is not None)
                    assert(fan.get("serial-number") is not None)
                    assert(fan.get("fw-revision") is not None)
                    assert(fan.get("hw-revision") is not None)
                    assert(fan.get("health") is not None)
                    assert(fan.get("health-reason") is not None)
                    assert(fan.get("health-recommendation") is not None)

@step(u'When I send in the psu sensor message to request the psu "([^"]*)" data')
def when_i_send_in_the_psu_actuator_message_to_request_the_psu_actuator_type_data(step, resource_type):
    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "2015-05-29 14:28:30.974749",
        "expires" : 500,

        "message": {
        "sspl_ll_debug": {
        "debug_component": "sensor",
        "debug_enabled": True
        },
        "response_dest": {
        },
        "sspl_ll_msg_header": {
        "msg_version": "1.0.0",
        "uuid": "16476007-a739-4785-b5c7-f3de189cdf9d",
        "schema_version": "1.0.0",
        "sspl_version": "1.0.0"
        },
        "request_path": {
                    "site_id": 0,
                    "node_id": 1,
                    "rack_id": 0
        },
        "actuator_request_type": {
            "storage_enclosure": {
                "enclosure_request": resource_type,
                "resource": "*"
                }
                }
            }
        }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

@step(u'Then I get the psu actuator JSON response message for psu instance "([^"]*)"')
def then_i_get_the_psu_atuator_json_response_message(step, resource_id):

    psu_actuator_msg = None

    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: {0}".format(ingressMsg))
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "enclosure:fru:psu":
                psu_actuator_msg = msg_type
                break

        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(psu_actuator_msg is not None)
    assert(psu_actuator_msg.get("host_id") is not None)
    assert(psu_actuator_msg.get("alert_type") is not None)
    assert(psu_actuator_msg.get("severity") is not None)
    assert(psu_actuator_msg.get("alert_id") is not None)
    psu_info = psu_actuator_msg.get("info")
    assert(psu_info is not None)
    assert(psu_info.get("site_id") is not None)
    assert(psu_info.get("cluster_id") is not None)
    assert(psu_info.get("rack_id") is not None)
    assert(psu_info.get("node_id") is not None)
    assert(psu_info.get("resource_type") is not None)
    assert(psu_info.get("resource_id") is not None)
    assert(psu_info.get("event_time") is not None)

    if resource_id != "*":
        psuId = resource_id
        assert(psu_info.get("resource_id") == psuId)
    else:
        assert(psu_info.get("resource_id") == "*")

    psu_actuator_specific_info_array = psu_actuator_msg.get("specific_info")
    assert(psu_actuator_specific_info_array is not None)

    assert(len(psu_actuator_specific_info_array) > 0)
    if resource_id != "*":
        assert(len(psu_actuator_specific_info_array) == 1)
    else:
        assert(len(psu_actuator_specific_info_array) > 1)

    for psu_specific_info in psu_actuator_specific_info_array:
        assert(psu_specific_info is not None)
        assert(psu_specific_info.get("dctemp") is not None)
        assert(psu_specific_info.get("dc33v") is not None)
        assert(psu_specific_info.get("fru-shortname") is not None)
        assert(psu_specific_info.get("health-reason") is not None)
        assert(psu_specific_info.get("serial-number") is not None)
        assert(psu_specific_info.get("mfg-date") is not None)
        assert(psu_specific_info.get("dash-level") is not None)
        assert(psu_specific_info.get("dom-id") is not None)
        assert(psu_specific_info.get("dc5i") is not None)
        assert(psu_specific_info.get("enclosure-id") is not None)
        assert(psu_specific_info.get("position-numeric") is not None)
        assert(psu_specific_info.get("durable-id") is not None)
        assert(psu_specific_info.get("configuration-serialnumber") is not None)
        assert(psu_specific_info.get("health") is not None)
        assert(psu_specific_info.get("location") is not None)
        assert(psu_specific_info.get("dc5v") is not None)
        assert(psu_specific_info.get("status-numeric") is not None)
        assert(psu_specific_info.get("revision") is not None)
        assert(psu_specific_info.get("mfg-location") is not None)
        assert(psu_specific_info.get("dc12v") is not None)
        assert(psu_specific_info.get("vendor") is not None)
        assert(psu_specific_info.get("description") is not None)
        assert(psu_specific_info.get("mfg-date-numeric") is not None)
        assert(psu_specific_info.get("object-name") is not None)
        assert(psu_specific_info.get("part-number") is not None)
        assert(psu_specific_info.get("health-recommendation") is not None)
        assert(psu_specific_info.get("health-numeric") is not None)
        assert(psu_specific_info.get("dc12i") is not None)
        assert(psu_specific_info.get("name") is not None)
        assert(psu_specific_info.get("fw-revision") is not None)
        assert(psu_specific_info.get("position") is not None)
        assert(psu_specific_info.get("model") is not None)
        assert(psu_specific_info.get("mfg-vendor-id") is not None)

@step(u'When I send Enclosure SAS Port message to request the current "([^"]*)" data')
def when_i_send_the_enclosure_sas_port_message_to_request_the_current_actuator_type_data(step, resource_type):
    egressMsg = {
      "username": "sspl-ll",
      "description": "Seagate Storage Platform Library - Low Level - Actuator Request",
      "title": "SSPL-LL Actuator Request",
      "expires": 3600,
      "signature": "None",
      "time": "2019-11-21 08:37:27.144640",
      "message": {
        "sspl_ll_debug": {
          "debug_component": "sensor",
          "debug_enabled": True
        },
        "response_dest": {},
        "sspl_ll_msg_header": {
          "msg_version": "1.0.0",
          "uuid": "2ba55744-8218-40c2-8c2c-ea7bddf79c09",
          "schema_version": "1.0.0",
          "sspl_version": "1.0.0"
        },
        "actuator_request_type": {
          "storage_enclosure": {
            "enclosure_request": "ENCL: enclosure:interface:sas",
            "resource": "Expansion Port"
          }
        }
      }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

@step(u'Then I get the Enclosure SAS ports JSON response message')
def then_i_get_the_enclosure_sas_ports_json_response_message(step):
    enclosure_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            enclosure_msg = ingressMsg.get("sensor_response_type")
            break
        except Exception as exception:
            time.sleep(4)
            print exception

    assert(enclosure_msg is not None)
    assert(enclosure_msg.get("alert_type") is not None)
    assert(enclosure_msg.get("alert_id") is not None)
    assert(enclosure_msg.get("host_id") is not None)
    assert(enclosure_msg.get("severity") is not None)
    assert(enclosure_msg.get("info") is not None)

    enclosure_sas_info = enclosure_msg.get("info")
    assert(enclosure_sas_info.get("event_time") is not None)
    assert(enclosure_sas_info.get("resource_id") is not None)
    assert(enclosure_sas_info.get("site_id") is not None)
    assert(enclosure_sas_info.get("node_id") is not None)
    assert(enclosure_sas_info.get("cluster_id") is not None)
    assert(enclosure_sas_info.get("rack_id") is not None)
    assert(enclosure_sas_info.get("resource_type") is not None)

    assert(enclosure_msg.get("specific_info") is not None)
    enclosure_specific_info = enclosure_msg.get("specific_info", {})
    if enclosure_specific_info:
        assert(enclosure_specific_info.get("status") is not None)
        assert(enclosure_specific_info.get("sas-port-type-numeric") is not None)
        assert(enclosure_specific_info.get("name") is not None)
        assert(enclosure_specific_info.get("enclosure-id") is not None)
        assert(enclosure_specific_info.get("durable-id") is not None)
        assert(enclosure_specific_info.get("health-reason") is not None)
        assert(enclosure_specific_info.get("sas-port-index") is not None)
        assert(enclosure_specific_info.get("controller") is not None)
        assert(enclosure_specific_info.get("health") is not None)
        assert(enclosure_specific_info.get("controller-numeric") is not None)
        assert(enclosure_specific_info.get("object-name") is not None)
        assert(enclosure_specific_info.get("health-numeric") is not None)
        assert(enclosure_specific_info.get("health-recommendation") is not None)
        assert(enclosure_specific_info.get("status-numeric") is not None)
        assert(enclosure_specific_info.get("sas-port-type") is not None)
