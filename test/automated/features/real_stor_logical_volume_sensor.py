# -*- coding: utf-8 -*-
from lettuce import *

import os
import json
import psutil
import time

# Add the top level directory to the sys.path to access classes
topdir = os.path.dirname(os.path.dirname(os.path.dirname \
            (os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, topdir)

from test.automated.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

@step(u'Given that SSPL is running')
def given_that_sspl_is_running(step):
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

@step(u'When I send in the logical volume sensor message to request the current "([^"]*)" data')
def when_i_send_in_the_logical_volume_sensor_message_to_request_the_current_sensor_type_data(step, sensor_type):
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

@step(u'Then I get the logical volume sensor JSON response message')
def then_i_get_the_logical_volume_sensor_json_response_message(step):

    logical_volume_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(2)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            logical_volume_sensor_msg = msg_type["enclosure_logical_volume_alert"]
            break
        except Exception as exception:
            time.sleep(4)
            print exception

    assert(logical_volume_sensor_msg is not None)
    assert(logical_volume_sensor_msg.get("alert_type") is not None)
    assert(logical_volume_sensor_msg.get("resource_type") is not None)

    info = logical_volume_sensor_msg.get("info")
    assert(info is not None)

    assert(info.get("object-name") is not None)
    assert(info.get("virtual-disk-name") is not None)
    assert(info.get("storage-pool-name") is not None)
    assert(info.get("volume-name") is not None)
    assert(info.get("size") is not None)
    assert(info.get("total-size") is not None)
    assert(info.get("allocated-size") is not None)
    assert(info.get("storage-type") is not None)
    assert(info.get("owner") is not None)
    assert(info.get("serial-number") is not None)
    assert(info.get("write-policy") is not None)
    assert(info.get("volume-type") is not None)
    assert(info.get("volume-class") is not None)
    assert(info.get("blocksize") is not None)
    assert(info.get("blocks") is not None)
    assert(info.get("capabilities") is not None)
    assert(info.get("virtual-disk-serial") is not None)
    assert(info.get("volume-description") is not None)
    assert(info.get("wwn") is not None)
    assert(info.get("progress") is not None)
    assert(info.get("raidtype") is not None)
    assert(info.get("health") is not None)
    assert(info.get("health-reason") is not None)
    assert(info.get("health-recommendation") is not None)
    assert(info.get("disk-group") is not None)
