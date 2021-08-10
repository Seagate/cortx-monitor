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

import os
import json
import time
import psutil
import signal
import subprocess

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
    assert condition in ("stop", "start", "running", "halted")
    #start_stop_service(name, condition)

    # Check that the state for sspl_ll service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspl_d" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['cmdline', 'status'])
            if "sspl_d" in str(pinfo['cmdline']) and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

@step('When I "([^"]*)" the "([^"]*)" service')
def when_i_action_the_name_service(step, action, name):
    start_stop_service(name, action)

@step('When I ungracefully halt the "([^"]*)" service with signal "([^"]*)"')
def when_i_ungracefully_halt_the_name_service_with_signal_signum(step, name, signum):
    found = False
    for proc in psutil.process_iter():
        if proc.name == name:
            proc.send_signal(int(signum))
            found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['name', 'status'])
            if pinfo['name'] == name:
                proc.send_signal(int(signum))


@step('Then I receive a service watchdog json msg with service name "([^"]*)" and state of "([^"]*)"')
def then_i_receive_a_service_watchdog_json_msg_with_service_name_name_and_state_of_condition(step, name, condition):

    service_name = None
    service_state = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(5)
        print("Received: %s" % ingressMsg)

        try:
            # Verify module name and thread response
            service_name = ingressMsg.get("sensor_response_type").get("service_watchdog").get("service_name")
            print("service_name: %s" % service_name)

            service_state = ingressMsg.get("sensor_response_type").get("service_watchdog").get("service_state")
            print("service_state: %s" % service_state)
            break
        except Exception as exception:
            print(exception)
    assert service_name == name
    assert service_state == condition

def start_stop_service(service_name, action):
    assert action in ("stop", "start", "running", "halted")

    # Obtain an instance of d-bus to communicate with systemd
    bus = SystemBus()

    # Obtain a manager interface to d-bus for communications with systemd
    systemd = bus.get_object('org.freedesktop.systemd1',
                             '/org/freedesktop/systemd1')
    manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')

    if action == "start" or \
        action == "running":
        manager.StartUnit(service_name + ".service", 'replace')
    else:
        manager.StopUnit(service_name + ".service", 'replace')

    time.sleep(3)
