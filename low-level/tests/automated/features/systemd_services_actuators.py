# -*- coding: utf-8 -*-
from lettuce import *

import os
import json
import psutil

# Add the top level directory to the sys.path to access classes
topdir = os.path.dirname(os.path.dirname(os.path.dirname \
            (os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, topdir)

from tests.automated.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from dbus import SystemBus, Interface, exceptions as debus_exceptions


@step(u'Given that the "([^"]*)" service is "([^"]*)" and SSPL_LL is running')
def given_that_the_name_service_is_condition_and_sspl_ll_is_running(step, name, condition):
    # Apply the condition to the service to guarantee a known starting state
    assert condition in ("running", "halted")
    start_stop_service(name, condition)

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
            pinfo = proc.as_dict(attrs=['name', 'status'])
            if pinfo['name'] == "sspl_ll_d" and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

@step(u'When I send in the actuator message to "([^"]*)" the "([^"]*)"')
def when_i_send_in_the_actuator_message_to_action_the_service(step, action, service):
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
            "actuator_request_type": {
                "service_controller": {
                    "service_name" : service,
                    "service_request": action
                }
            }
        }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

@step(u'Then SSPL_LL "([^"]*)" the "([^"]*)" and I get the service is "([^"]*)" response')
def then_sspl_ll_action_the_service_and_i_get_the_service_is_condition_response(step, action, service, condition):
    ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
    print("Received: %s" % ingressMsg)

    # Verify module name and thread response
    service_name = ingressMsg.get("actuator_response_type").get("service_controller").get("service_name")
    print("service_name: %s" % service_name)
    assert service_name == service

    service_response = ingressMsg.get("actuator_response_type").get("service_controller").get("service_response")
    print("service_response: %s" % service_response)
    assert service_response == condition


def start_stop_service(service_name, action):
    assert action in ("running", "halted")
    
    # Obtain an instance of d-bus to communicate with systemd
    bus = SystemBus()

    # Obtain a manager interface to d-bus for communications with systemd
    systemd = bus.get_object('org.freedesktop.systemd1',
                             '/org/freedesktop/systemd1')
    manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')
    
    if action == "running":
        manager.StartUnit(service_name + ".service", 'replace')
    else:
        manager.StopUnit(service_name + ".service", 'replace')


    