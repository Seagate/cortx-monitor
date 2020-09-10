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

import os
import time

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from sspl_test.common import check_sspl_ll_is_running

from alerts.self_hw.self_hw_utilities import run_cmd
from sspl_test.framework.base.sspl_constants import SSPL_TEST_PATH

def init(args):
    pass

def wait_for_asserted_event():
    time.sleep(0.1)
    ingressMsg = {}
    got_alert = False
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "node:fru:fan":
                info = msg_type["info"]
                specific_info = msg_type["specific_info"]
                if info["resource_type"] == "node:fru:fan" and \
                        specific_info["event"] == "Lower Critical going low":
                    # We got the expected alert
                    got_alert = True
                    break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)
    return got_alert

def wait_for_deasserted_event():
    time.sleep(0.1)
    ingressMsg = {}
    got_alert = False
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "node:fru:fan":
                info = msg_type["info"]
                specific_info = msg_type["specific_info"]
                if info["resource_type"] == "node:fru:fan" and \
                        specific_info["event"] == "Lower Critical going high":
                    # We got the expected alert
                    got_alert = True
                    break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)
    return got_alert

def test_self_hw_node_sel_event(args):
    check_sspl_ll_is_running()
    # fetch a good resource fron ipmitool
    result = run_cmd('ipmitool sdr type Fan')
    test_resource = None
    if result:
        for resource in result:
            if 'ok' in resource.decode().lower():
                # this is the first ok resource, use it
                test_resource = resource.decode().split('|')[0].strip()
                break
        # inject event into sel list and wait for alert
        print(f"Using test resource {test_resource}")
        run_cmd(f"ipmitool event '{test_resource}' lcr")
        # wait for fault alert
        start_time = time.time()
        asserted = False
        while time.time() - start_time < 60: # wait for 60 seconds
            if wait_for_asserted_event():
                asserted = True
                break
        if not asserted:
            print("Did not get asserted event alert.")
            assert(False)
        # revert the event
        run_cmd(f"ipmitool event '{test_resource}' lcr deassert")
        # wait for alert
        start_time = time.time()
        deasserted = False
        while time.time() - start_time < 60: # wait for 60 seconds
            if wait_for_deasserted_event():
                deasserted = True
                break
        if not deasserted:
            print("Did not get asserted event alert.")
            assert(False)
    else:
        print("ipmitool returned no results.")
        assert(False)

test_list = [test_self_hw_node_sel_event]
