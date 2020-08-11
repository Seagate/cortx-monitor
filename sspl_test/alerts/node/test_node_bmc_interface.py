# -*- coding: utf-8 -*-
import json
import os
import psutil
import time
import sys
import subprocess

from sspl_test.default import world
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from sspl_test.common import check_sspl_ll_is_running

from sspl_test.framework.base.sspl_constants import CONSUL_PATH
from sspl_test.alerts.node import simulate_bmc_interface_alert

def init(args):
    pass

def test_bmc_interface(args):
    check_sspl_ll_is_running()
    # backup active bmc interface
    BMC_IF_CONSUL_KEY,BMC_IF_CONSUL_VAL = backup_bmc_config()

    if BMC_IF_CONSUL_VAL == "lan":
        # backup lan fault value
        lan_fault_consul_key , lan_fault_val = backup_lan_fault()
        if lan_fault_consul_key and lan_fault_val is not None:
            simulate_bmc_interface_alert.clean_previous_lan_alert(lan_fault_consul_key , lan_fault_val)
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
    simulate_bmc_interface_alert.restore_config(BMC_IF_CONSUL_KEY,BMC_IF_CONSUL_VAL)
    if BMC_IF_CONSUL_VAL == "lan":
        simulate_bmc_interface_alert.restore_config(lan_fault_consul_key , lan_fault_val)

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

    bmc_interface_specific_info = bmc_interface_message.get("specific_info")
    if bmc_interface_specific_info:
        assert(bmc_interface_specific_info.get("event") is not None)

def backup_bmc_config():
    # read active bmc interface
    cmd = f"{CONSUL_PATH}/consul kv get --recurse ACTIVE_BMC_IF"
    bmc_interface,retcode = run_cmd(cmd)
    if retcode != 0:
        print(f"command:{cmd} not executed successfully")
        return

    # bmc_interface = [b'ACTIVE_BMC_IF_001', b'\x80\x03X\x06\x00\x00\x00systemq\x00.\n']
    # fetch interface consul key and value from bmc_interface
    active_bmc_IF_key = bmc_interface[0].decode()
    # parse string b'\x80\x03X\x06\x00\x00\x00systemq\x00.\n' to fetch bmc interface value
    if b'system' in bmc_interface[1]:
        active_bmc_IF_value = bmc_interface[1].replace(bmc_interface[1],b'system').decode()
    elif b'lan' in bmc_interface[1]:
        active_bmc_IF_value = bmc_interface[1].replace(bmc_interface[1], b'lan').decode()

    return active_bmc_IF_key, active_bmc_IF_value

def backup_lan_fault():
    # check for previous lan fault.
    # If already fault alert raised for lan, clear it to raise fault again for test case excution.
    cmd = f"{CONSUL_PATH}/consul kv get --recurse LAN_ALERT"
    res, retcode = run_cmd(cmd)
    if retcode != 0:
        print(f"command:{cmd} not executed successfully")
        return
    # If there is no alert raised for lan. keep key and value as None.
    if len(res) == 1:
        lan_fault_key = None
        lan_fault_value = None
    else:
        # res = [b'LAN_ALERT_001', b'\x80\x03X\x05\x00\x00\x00faultq\x00.\n']
        lan_fault_key = res[0].decode()
        if b'fault' in res[1]:
            lan_fault_value = res[1].replace(res[1], b'fault').decode()
        else:
            lan_fault_value = None

    return lan_fault_key, lan_fault_value

def run_cmd(cmd):
    process = subprocess.Popen(cmd, shell=True , stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    result = process.communicate()
    result = b''.join([val for val in result if val]).split(b':')
    retcode = process.returncode
    return result,retcode

test_list = [test_bmc_interface]
