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
def when_i_send_in_the_logical_volume_sensor_message_to_request_the_current_sensor_type_data(step, resource_type):
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
            logical_volume_sensor_msg = ingressMsg.get("sensor_response_type")
            break
        except Exception as exception:
            time.sleep(4)
            print exception

    assert(logical_volume_sensor_msg is not None)
    assert(logical_volume_sensor_msg.get("alert_type") is not None)
    assert(logical_volume_sensor_msg.get("alert_id") is not None)
    assert(logical_volume_sensor_msg.get("severity") is not None)
    assert(logical_volume_sensor_msg.get("host_id") is not None)
    assert(logical_volume_sensor_msg.get("info") is not None)
    assert(logical_volume_sensor_msg.get("specific_info") is not None)

    info = logical_volume_sensor_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = logical_volume_sensor_msg.get("specific_info")
    assert(specific_info.get("object-name") is not None)
    assert(specific_info.get("virtual-disk-name") is not None)
    assert(specific_info.get("storage-pool-name") is not None)
    assert(specific_info.get("volume-name") is not None)
    assert(specific_info.get("size") is not None)
    assert(specific_info.get("total-size") is not None)
    assert(specific_info.get("allocated-size") is not None)
    assert(specific_info.get("storage-type") is not None)
    assert(specific_info.get("owner") is not None)
    assert(specific_info.get("serial-number") is not None)
    assert(specific_info.get("write-policy") is not None)
    assert(specific_info.get("volume-type") is not None)
    assert(specific_info.get("volume-class") is not None)
    assert(specific_info.get("blocksize") is not None)
    assert(specific_info.get("blocks") is not None)
    assert(specific_info.get("capabilities") is not None)
    assert(specific_info.get("virtual-disk-serial") is not None)
    assert(specific_info.get("volume-description") is not None)
    assert(specific_info.get("wwn") is not None)
    assert(specific_info.get("progress") is not None)
    assert(specific_info.get("raidtype") is not None)
    assert(specific_info.get("health") is not None)
    assert(specific_info.get("health-reason") is not None)
    assert(specific_info.get("health-recommendation") is not None)
    assert(specific_info.get("disk-group") is not None)
