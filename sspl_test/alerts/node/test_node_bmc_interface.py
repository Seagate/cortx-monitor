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
import json
import os
import psutil
import time
import sys
import subprocess

from default import world
from rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from common import check_sspl_ll_is_running
from framework.base.sspl_constants import DATA_PATH
from alerts.node import simulate_bmc_interface_alert


def init(args):
    pass

def test_bmc_interface(args):
    check_sspl_ll_is_running()
    # backup active bmc interface
    BMC_IF_CONSUL_KEY,BMC_IF_CONSUL_VAL = backup_bmc_config()

    if BMC_IF_CONSUL_VAL == "lan":
        simulate_bmc_interface_alert.lan_channel_alert(BMC_IF_CONSUL_KEY,BMC_IF_CONSUL_VAL)
    else:
        simulate_bmc_interface_alert.kcs_channel_alert(BMC_IF_CONSUL_KEY,BMC_IF_CONSUL_VAL)

    bmc_interface_message = None
    time.sleep(25)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == "node:bmc:interface:kcs" or \
                msg_type["info"]["resource_type"] == "node:bmc:interface:rmcp":
                bmc_interface_message = msg_type
                break
        except Exception as exception:
            time.sleep(0.1)
            print(exception)

    #restore bmc config and activate ipmisimtool
    simulate_bmc_interface_alert.restore_config()

    assert(bmc_interface_message is not None)
    assert(bmc_interface_message.get("alert_type") is not None)
    alert_type = bmc_interface_message.get("alert_type")
    assert(alert_type=="fault")
    assert(bmc_interface_message.get("alert_id") is not None)
    assert(bmc_interface_message.get("severity") is not None)
    assert(bmc_interface_message.get("host_id") is not None)
    assert(bmc_interface_message.get("info") is not None)

    bmc_interface_info = bmc_interface_message.get("info")
    assert(bmc_interface_info.get("site_id") is not None)
    assert(bmc_interface_info.get("rack_id") is not None)
    assert(bmc_interface_info.get("node_id") is not None)
    assert(bmc_interface_info.get("cluster_id") is not None)
    assert(bmc_interface_info.get("resource_id") is not None)
    assert(bmc_interface_info.get("description") is not None )

    bmc_interface_specific_info = bmc_interface_message.get("specific_info")
    if bmc_interface_specific_info:
        assert(bmc_interface_specific_info.get("channel info") is not None)

def backup_bmc_config():
    # read active bmc interface
    cmd = f"cat {DATA_PATH}/server/ACTIVE_BMC_IF_*"
    bmc_interface,retcode = run_cmd(cmd)
    bmc_interface = bmc_interface[0]
    if retcode != 0:
        print(f"command:{cmd} not executed successfully")
        return

    # bmc_interface = b'\x80\x03X\x06\x00\x00\x00systemq\x00.\n'
    # fetch interface key and value from bmc_interface
    active_bmc_IF_key = f'{DATA_PATH}/server/ACTIVE_BMC_IF'
    # parse string b'\x80\x03X\x06\x00\x00\x00systemq\x00.\n' to fetch bmc interface value
    if b'system' in bmc_interface:
        active_bmc_IF_value = bmc_interface.replace(bmc_interface,b'system').decode()
    elif b'lan' in bmc_interface:
        active_bmc_IF_value = bmc_interface.replace(bmc_interface, b'lan').decode()

    return active_bmc_IF_key, active_bmc_IF_value

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True , stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = process.communicate()
    result = b''.join([val for val in result if val]).split(b':')
    retcode = process.returncode
    return result,retcode

test_list = [test_bmc_interface]
