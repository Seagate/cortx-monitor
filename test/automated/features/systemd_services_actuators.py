# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

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
from dbus import SystemBus, Interface, exceptions as debus_exceptions


@step('Given that the "([^"]*)" service is "([^"]*)" and SSPL_LL is running')
def given_that_the_name_service_is_condition_and_sspl_ll_is_running(step, name, condition):
    # Apply the condition to the service to guarantee a known starting state
    assert condition in ("running", "halted")
    start_stop_service(name, condition)

    # Check that the state for sspl_ll service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspld" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['cmdline', 'status'])
            if "sspld" in str(pinfo['cmdline']) and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

@step('When I send in the actuator message to "([^"]*)" the "([^"]*)"')
def when_i_send_in_the_actuator_message_to_action_the_service(step, action, service):
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
            "actuator_request_type": {
                "service_controller": {
                    "service_name" : service,
                    "service_request": action
                }
            }
        }
    }
    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)


@step('Then SSPL_LL "([^"]*)" the "([^"]*)" and I get the service is "([^"]*)" response')
def then_sspl_ll_action_the_service_and_i_get_the_service_is_condition_response(step, action, service, condition):

    service_name = None
    service_response = None
    time.sleep(10)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(10)
        print("Received: %s" % ingressMsg)

        try:
            # Verify module name and thread response
            msg = ingressMsg.get("actuator_response_type").get("service_controller")
            service_name = msg["service_name"]
            time.sleep(10)
            print("service_name: %s" % service_name)

            msg = ingressMsg.get("actuator_response_type").get("service_controller")
            service_response = msg["service_response"]
            #time.sleep(4)
            print("service_response: %s" % service_response)
            break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert service_name == service
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
