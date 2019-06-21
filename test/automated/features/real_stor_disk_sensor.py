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


@step(u'When I send in the disk sensor message to request the current "([^"]*)" data')
def when_i_send_in_the_disk_sensor_message_to_request_the_current_sensor_type_data(step, sensor_type):
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
                "enclosure_alert": {
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

            if sensor == "enclosure_disk_alert":
                disk_sensor_msg = ingressMsg.get("sensor_response_type").get("enclosure_disk_alert")
                assert(disk_sensor_msg is not None)
                assert(disk_sensor_msg.get("alert_type") is not None)
                assert(disk_sensor_msg.get("resource_type") is not None)
                assert(disk_sensor_msg.get("info") is not None)
                assert(disk_sensor_msg.get("info").get("description") is not None)
                assert(disk_sensor_msg.get("info").get("slot") is not None)
                assert(disk_sensor_msg.get("info").get("status") is not None)
                assert(disk_sensor_msg.get("info").get("architecture") is not None)
                assert(disk_sensor_msg.get("info").get("serial-number") is not None)
                assert(disk_sensor_msg.get("info").get("size") is not None)
                assert(disk_sensor_msg.get("info").get("vendor") is not None)
                assert(disk_sensor_msg.get("info").get("model") is not None)
                assert(disk_sensor_msg.get("info").get("revision") is not None)
                assert(disk_sensor_msg.get("info").get("temperature") is not None)
                assert(disk_sensor_msg.get("info").get("LED-status") is not None)
                assert(disk_sensor_msg.get("info").get("locator-LED") is not None)
                assert(disk_sensor_msg.get("info").get("blink-state") is not None)
                assert(disk_sensor_msg.get("info").get("SMART") is not None)
                assert(disk_sensor_msg.get("info").get("health") is not None)
                assert(disk_sensor_msg.get("info").get("health-reason") is not None)
                assert(disk_sensor_msg.get("info").get("health-recommendation") is not None)
                assert(disk_sensor_msg.get("info").get("enclosure-family") is not None)
                assert(disk_sensor_msg.get("info").get("enclosure-id") is not None)
                assert(disk_sensor_msg.get("info").get("enclosure-wwn") is not None)

            else:
                assert False, "Response not recognized"
            break
        except Exception as exception:
            print exception
