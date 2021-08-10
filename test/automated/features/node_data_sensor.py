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
import simulate_network_interface as mock_eth_interface
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


@step(u'When I send in the node data sensor message to request the current "([^"]*)" data')
def when_i_send_in_the_node_data_sensor_message_to_request_the_current_sensor_type_data(step, sensor_type):
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
    assert(host_update_msg.get("alert_type") is not None)
    assert(host_update_msg.get("alert_id") is not None)
    assert(host_update_msg.get("severity") is not None)
    assert(host_update_msg.get("host_id") is not None)
    assert(host_update_msg.get("info") is not None)
    assert(host_update_msg.get("specific_info") is not None)
    info = host_update_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)
    specific_info = host_update_msg.get("specific_info")
    assert(specific_info.get("loggedInUsers") is not None)
    assert(specific_info.get("totalMemory") is not None)
    assert(specific_info.get("runningProcessCount") is not None)
    assert(specific_info.get("uname") is not None)
    assert(specific_info.get("bootTime") is not None)
    assert(specific_info.get("processCount") is not None)
    assert(specific_info.get("localtime") is not None)

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
    assert(cpu_data_msg.get("alert_type") is not None)
    assert(cpu_data_msg.get("alert_id") is not None)
    assert(cpu_data_msg.get("severity") is not None)
    assert(cpu_data_msg.get("host_id") is not None)
    assert(cpu_data_msg.get("info") is not None)
    assert(cpu_data_msg.get("specific_info") is not None)
    info = cpu_data_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)
    specific_info = cpu_data_msg.get("specific_info")
    assert(specific_info.get("systemTime") is not None)
    assert(specific_info.get("interruptTime") is not None)
    assert(specific_info.get("userTime") is not None)
    assert(specific_info.get("idleTime") is not None)
    assert(specific_info.get("csps") is not None)
    assert(specific_info.get("iowaitTime") is not None)
    assert(specific_info.get("niceTime") is not None)
    assert(specific_info.get("cpu_usage") is not None)
    assert(specific_info.get("coreData") is not None)
    assert(specific_info.get("localtime") is not None)
    assert(specific_info.get("softirqTime") is not None)
    assert(specific_info.get("stealTime") is not None)

@step(u'Then I get the if data sensor JSON response message')
def then_i_get_the_if_data_sensor_json_response_message(step):

    if_data_msg = None
    #create and shuffle mocked network interface to get network alerts
    mock_eth_interface.shuffle_nw_interface()
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(10)
        print("Received: {0}".format(ingressMsg))
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "node:interface:nw":
                if_data_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(if_data_msg is not None)
    assert(if_data_msg.get("alert_type") is not None)
    assert(if_data_msg.get("alert_id") is not None)
    assert(if_data_msg.get("severity") is not None)
    assert(if_data_msg.get("host_id") is not None)
    assert(if_data_msg.get("info") is not None)
    assert(if_data_msg.get("specific_info") is not None)

    if_data_info = if_data_msg.get("info")
    assert(if_data_info.get("site_id") is not None)
    assert(if_data_info.get("node_id") is not None)
    assert(if_data_info.get("cluster_id") is not None)
    assert(if_data_info.get("rack_id") is not None)
    assert(if_data_info.get("resource_type") is not None)
    assert(if_data_info.get("event_time") is not None)
    assert(if_data_info.get("resource_id") is not None)

    if_data_specific_info = if_data_msg.get("specific_info")
    assert(if_data_specific_info is not None)
    assert(if_data_specific_info.get("localtime") is not None)
    assert(if_data_specific_info.get("interfaces") is not None)


@step(u'Then I get the disk space data sensor JSON response message')
def then_i_get_the_disk_space_data_sensor_json_response_message(step):

    disk_space_sensor_msg = None
    time.sleep(4)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(10)
        print("Received: {0}".format(ingressMsg))

        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "node:os:disk_space":
                disk_space_sensor_msg = msg_type
                break
        except Exception as exception:
            time.sleep(4)
            print(exception)

    assert(disk_space_sensor_msg is not None)
    assert(disk_space_sensor_msg.get("alert_type") is not None)
    assert(disk_space_sensor_msg.get("alert_id") is not None)
    assert(disk_space_sensor_msg.get("severity") is not None)
    assert(disk_space_sensor_msg.get("host_id") is not None)
    assert(disk_space_sensor_msg.get("info") is not None)
    assert(disk_space_sensor_msg.get("specific_info") is not None)

    disk_space_info = disk_space_sensor_msg.get("info")
    assert(disk_space_info.get("site_id") is not None)
    assert(disk_space_info.get("node_id") is not None)
    assert(disk_space_info.get("cluster_id") is not None)
    assert(disk_space_info.get("rack_id") is not None)
    assert(disk_space_info.get("resource_type") is not None)
    assert(disk_space_info.get("event_time") is not None)
    assert(disk_space_info.get("resource_id") is not None)

    disk_space_specific_info = disk_space_sensor_msg.get("specific_info")
    assert(disk_space_specific_info is not None)
    assert(disk_space_specific_info.get("freeSpace") is not None)
    assert(disk_space_specific_info.get("totalSpace") is not None)
    assert(disk_space_specific_info.get("diskUsedPercentage") is not None)
