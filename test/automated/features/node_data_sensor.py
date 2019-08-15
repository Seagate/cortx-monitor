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

@step(u'Given that SSPL-LL is running')
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


@step(u'When I send in the node data sensor message to request the current "([^"]*)" data')
def when_i_send_in_the_node_data_sensor_message_to_request_the_current_sensor_type_data(step, sensor_type):
    egressMsg = {
        "title": "SSPL-LL Actuator Request",
        "description": "Seagate Storage Platform Library - Low Level - Actuator Request",

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
            "sensor_request_type": {
                "node_data": {
                    "sensor_type": sensor_type
                }
            }
        }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)


@step(u'Then I get the host update data sensor JSON response message')
def then_i_get_the_host_update_data_sensor_json_response_message(step):

    host_update_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(10)
        print("Received: {0}".format(ingressMsg))

        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            host_update_msg = msg_type["host_update"]
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(host_update_msg is not None)
    assert(host_update_msg.get("hostId") is not None)
    assert(host_update_msg.get("localtime") is not None)
    assert(host_update_msg.get("bootTime") is not None)
    assert(host_update_msg.get("upTime") is not None)
    assert(host_update_msg.get("uname") is not None)
    assert(host_update_msg.get("freeMem") is not None)
    assert(host_update_msg.get("loggedInUsers") is not None)
    assert(host_update_msg.get("processCount") is not None)
    assert(host_update_msg.get("runningProcessCount") is not None)

@step(u'Then I get the local mount data sensor JSON response message')
def then_i_get_the_local_mount_data_sensor_json_response_message(step):

    local_mount_data_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(10)
        print("Received: {0}".format(ingressMsg))

        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            local_mount_data_msg = msg_type["local_mount_data"]
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(local_mount_data_msg is not None)
    assert(local_mount_data_msg.get("hostId") is not None)
    assert(local_mount_data_msg.get("localtime") is not None)
    assert(local_mount_data_msg.get("freeSpace") is not None)
    assert(local_mount_data_msg.get("freeInodes") is not None)
    assert(local_mount_data_msg.get("freeSwap") is not None)
    assert(local_mount_data_msg.get("totalSpace") is not None)
    assert(local_mount_data_msg.get("totalSwap") is not None)

@step(u'Then I get the cpu data sensor JSON response message')
def then_i_get_the_cpu_data_sensor_json_response_message(step):

    cpu_data_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(10)
        print("Received: {0}".format(ingressMsg))

        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            cpu_data_msg = msg_type["cpu_data"]
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(cpu_data_msg is not None)
    assert(cpu_data_msg.get("hostId") is not None)
    assert(cpu_data_msg.get("localtime") is not None)
    assert(cpu_data_msg.get("csps") is not None)
    assert(cpu_data_msg.get("idleTime") is not None)
    assert(cpu_data_msg.get("interruptTime") is not None)
    assert(cpu_data_msg.get("iowaitTime") is not None)
    assert(cpu_data_msg.get("niceTime") is not None)
    assert(cpu_data_msg.get("softirqTime") is not None)
    assert(cpu_data_msg.get("stealTime") is not None)
    assert(cpu_data_msg.get("systemTime") is not None)
    assert(cpu_data_msg.get("userTime") is not None)
    assert(cpu_data_msg.get("coreData") is not None)

@step(u'Then I get the if data sensor JSON response message')
def then_i_get_the_if_data_sensor_json_response_message(step):

    if_data_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(10)
        print("Received: {0}".format(ingressMsg))

        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if_data_msg = msg_type["if_data"]
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(if_data_msg is not None)
    assert(if_data_msg.get("hostId") is not None)
    assert(if_data_msg.get("localtime") is not None)
    assert(if_data_msg.get("interfaces") is not None)

@step(u'Then I get the disk space data sensor JSON response message')
def then_i_get_the_disk_space_data_sensor_json_response_message(step):

    disk_space_data_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(10)
        print("Received: {0}".format(ingressMsg))

        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            disk_space_data_msg = msg_type["disk_space_alert"]
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(disk_space_data_msg is not None)
    assert(disk_space_data_msg.get("hostId") is not None)
    assert(disk_space_data_msg.get("localtime") is not None)
    assert(disk_space_data_msg.get("freeSpace") is not None)
    assert(disk_space_data_msg.get("totalSpace") is not None)
    assert(disk_space_data_msg.get("diskUsedPercentage") is not None)

