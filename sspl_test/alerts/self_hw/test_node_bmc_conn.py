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

# Connectivity to BMC is checked via SSPL during restart
# We can restart SSPL and wait for an alert from SSPL if there is a failure
# If there is no failure, that would mean connectivity is OK

import os
import re
import time
import socket
import subprocess

from default import world
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests
from common import check_sspl_ll_is_running
from framework.utils.conf_utils import (
    Conf, GLOBAL_CONF, ENCLOSURE, MACHINE_ID, BMC_IP_KEY, BMC_USER_KEY, BMC_SECRET_KEY)
from cortx.utils.process import SimpleProcess
from cortx.utils.security.cipher import Cipher
from cortx.utils.validator.v_bmc import BmcV

sensor_type = "node:bmc:interface:kcs"

def init(args):
    pass

def test_bmc_accessible_through_kcs(args):
    check_sspl_ll_is_running()
    node_data_sensor_message_request(sensor_type)
    bmc_interface_message = None
    while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
        time.sleep(0.1)
        print("Received: %s" % ingressMsg)
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type["info"]["resource_type"] == sensor_type:
                bmc_interface_message = msg_type
                break
        except Exception as exception:
            print(exception)

    assert(bmc_interface_message is not None)
    assert(bmc_interface_message.get("alert_type") is not None)
    assert(bmc_interface_message.get("alert_id") is not None)
    assert(bmc_interface_message.get("severity") is not None)
    assert(bmc_interface_message.get("host_id") is not None)
    assert(bmc_interface_message.get("info") is not None)

    bmc_interface_info = bmc_interface_message.get("info")
    assert(bmc_interface_info.get("site_id") is not None)
    assert(bmc_interface_info.get("rack_id") is not None)
    assert(bmc_interface_info.get("node_id") is not None)
    assert(bmc_interface_info.get("cluster_id") is not None)
    assert(bmc_interface_info.get("resource_i") is not None)
    assert(bmc_interface_info.get("description") is not None )

    # KCS channel specifc validations
    bmc_interface_specific_info = bmc_interface_message.get("specific_info")
    assert(bmc_interface_specific_info.get("channel info") is not None)
    channel_info = bmc_interface_specific_info.get("channel info")
    assert(channel_info.get("Channel Protocol Type") == "KCS")
    alert_type = bmc_interface_message.get("alert_type")
    assert(alert_type != "fault")

def node_data_sensor_message_request(sensor_type):
    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "2021-04-22 11:25:28.852492",
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

    world.sspl_modules[EgressProcessorTests.name()]._write_internal_msgQ(
        EgressProcessorTests.name(), egressMsg)

def test_bmc_config(args):
    """Check if BMC configuration are valid."""
    pkey_file = "/root/.ssh/id_rsa_prvsnr"
    if not os.path.exists(pkey_file):
        print("\tSkipping test_bmc_config.. pkey file not found.")
        return
    bmc_ip = Conf.get(GLOBAL_CONF, BMC_IP_KEY)
    bmc_user = Conf.get(GLOBAL_CONF, BMC_USER_KEY)
    bmc_secret = Conf.get(GLOBAL_CONF, BMC_SECRET_KEY)
    bmc_key = Cipher.generate_key(MACHINE_ID, "server_node")
    bmc_passwd = Cipher.decrypt(
        bmc_key, bmc_secret.encode("utf-8")).decode("utf-8")
    BmcV().validate(
        "accessible", [socket.getfqdn(), bmc_ip, bmc_user, bmc_passwd])

def test_bmc_firmware_version(args):
    """Check if BMC firmware version is 1.71."""
    cmd = "ipmitool bmc info"  # Firmware Revision : 1.71
    expected_ver = "1.71"
    version_found = None
    res_op, res_err, res_rc = SimpleProcess(cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"Firmware Revision[\s]+:[\s]+([\w.]+)(.*)", res_op)
        if search_res:
            version_found = search_res.groups()[0]
    else:
        raise Exception("ERROR: %s" % res_err.decode())
    if expected_ver != version_found:
        print("Expected: %s Actual: %s" % (expected_ver, version_found))
        assert False

def test_bmc_channel_type_is_kcs(args):
    """Check if BMC channel type is KCS."""
    cmd = "sudo ipmitool channel info"  # Channel Protocol Type : KCS
    expected_channel = "KCS"
    channel_found = None
    res_op, res_err, res_rc = SimpleProcess(cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"Channel Protocol Type[\s]+:[\s]+(\w+)(.*)", res_op)
        if search_res:
            channel_found = search_res.groups()[0]
    else:
        raise Exception("ERROR: %s" % res_err.decode())
    if expected_channel != channel_found:
        print("Expected: %s Actual: %s" % (expected_channel, channel_found))
        assert False

test_list = [
    test_bmc_config,
    test_bmc_firmware_version,
    test_bmc_channel_type_is_kcs,
    test_bmc_accessible_through_kcs
    ]
