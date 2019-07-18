# -*- coding: utf-8 -*-
from lettuce import *

import os
import json
import psutil

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


@step(u'Then I get the "([^"]*)" JSON response message')
def then_i_get_the_sensor_json_response_message(step, sensor):
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        print("Received: %s" % ingressMsg)

        try:
            # Make sure we get back the message type that matches the request
            msgType = ingressMsg.get("sensor_response_type")
            assert(msgType != None)

            if sensor == "host_update":
                host_update_msg = ingressMsg.get("sensor_response_type").get("host_update")
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

            elif sensor == "local_mount_data":
                local_mount_data_msg = ingressMsg.get("sensor_response_type").get("local_mount_data")
                assert(local_mount_data_msg is not None)
                assert(local_mount_data_msg.get("hostId") is not None)
                assert(local_mount_data_msg.get("localtime") is not None)
                assert(local_mount_data_msg.get("freeSpace") is not None)
                assert(local_mount_data_msg.get("freeInodes") is not None)
                assert(local_mount_data_msg.get("freeSwap") is not None)
                assert(local_mount_data_msg.get("totalSpace") is not None)
                assert(local_mount_data_msg.get("totalSwap") is not None)

            elif sensor == "cpu_data":
                cpu_data_msg = ingressMsg.get("sensor_response_type").get("cpu_data")
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

            elif sensor == "if_data":
                if_data_msg = ingressMsg.get("sensor_response_type").get("if_data")
                assert(if_data_msg is not None)
                assert(if_data_msg.get("hostId") is not None)
                assert(if_data_msg.get("localtime") is not None)
                assert(if_data_msg.get("interfaces") is not None)
            else:
                assert False, "Response not recognized"
            break
        except Exception as exception:
            print exception
