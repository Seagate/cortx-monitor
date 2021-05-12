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
import socket

from framework.utils.conf_utils import (
    Conf, SSPL_CONF, GLOBAL_CONF, MACHINE_ID, BMC_IP_KEY,
    BMC_USER_KEY, BMC_SECRET_KEY)
from alerts.self_hw.self_hw_utilities import get_manufacturer_name
from cortx.utils.process import SimpleProcess
from cortx.utils.security.cipher import Cipher
from cortx.utils.validator.v_bmc import BmcV


CHANNEL_PROTOCOL = "Channel Protocol Type"
CHANNEL_MEDIUM = "Channel Medium Type"
FIRMWARE_VERSION = "Firmware Revision"

def init(args):
    pass

def test_bmc_config(args):
    """Check if BMC configuration are valid."""
    pkey_file = "/root/.ssh/id_rsa"
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
            r"%s[\s]+:[\s]+([\w.]+)(.*)" % FIRMWARE_VERSION, res_op)
        if search_res:
            version_found = search_res.groups()[0]
    else:
        raise Exception("ERROR: %s" % res_err.decode())
    if expected_ver != version_found:
        print("UNEXPECTED BMC FIRMWARE VERSION FOUND.")
        print("Expected: %s" % expected_ver)
        print("Found: %s" % version_found)

def test_bmc_is_accessible(args):
    """Check if BMC is accessible through KCS or LAN."""
    channel_interface = Conf.get(
        SSPL_CONF, "BMC_INTERFACE>default", 'system')

    if channel_interface == "system":
        # Check BMC is accessible through KCS
        cmd = "sudo ipmitool channel info"
        expected_channel = "KCS"
        channel_found = None
        res_op, res_err, res_rc = SimpleProcess(cmd).run()
        if res_rc == 0:
            res_op = res_op.decode()
            search_res = re.search(
                r"%s[\s]+:[\s]+(\w+)(.*)" % CHANNEL_PROTOCOL, res_op)
            if search_res:
                channel_found = search_res.groups()[0]
            if expected_channel != channel_found:
                print("UNEXPECTED BMC CHANNEL TYPE FOUND.")
                print("Expected: %s" % expected_channel)
                print("Found: %s" % channel_found)
        else:
            res_err = res_err.decode()
            kcs_errors = ("could not find inband device", "driver timeout")
            if not any(err for err in kcs_errors if err in res_err):
                raise Exception("ERROR: %s" % res_err)
    elif channel_interface == "lan":
        # Check BMC is accessible through LAN
        subcommand = "channel info"
        bmc_ip = Conf.get(GLOBAL_CONF, BMC_IP_KEY)
        bmc_user = Conf.get(GLOBAL_CONF, BMC_USER_KEY)
        bmc_secret = Conf.get(GLOBAL_CONF, BMC_SECRET_KEY)
        bmc_key = Cipher.generate_key(MACHINE_ID, "server_node")
        bmc_passwd = Cipher.decrypt(
            bmc_key, bmc_secret.encode("utf-8")).decode("utf-8")
        cmd = "sudo ipmitool -H %s -U %s -P %s -I lan %s" %(
            bmc_ip, bmc_user, bmc_passwd, subcommand)
        res_op, res_err, res_rc = SimpleProcess(cmd).run()
        if res_rc != 0:
            raise Exception("ERROR: %s" % res_err.decode())

def test_chassis_selftest(args):
    """Check chassis selttestsel is passed."""
    cmd = "ipmitool chassis selftest"
    expected_res = "Self Test Results    : passed"
    res_op, res_err, res_rc = SimpleProcess(cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        if expected_res not in res_op:
            assert False, res_op
    else:
        raise Exception("ERROR: %s" % res_err.decode())

def test_sensor_availability(args):
    """Fail if any expected sensor is not detected by ipmitool."""
    found_all_sensors = True
    sensors = [
        "Voltage",
        "Temperature",
        "Power Supply",
        "Drive Slot / Bay",
        "Fan"
        ]
    # Get manufacturer name
    manufacturer = get_manufacturer_name()
    for sensor in sensors:
        cmd = ["ipmitool", "sdr", "type", sensor]
        res_op, res_err, res_rc = SimpleProcess(cmd).run()
        if res_rc == 0:
            res_op = res_op.decode().replace("\n", "")
            if not res_op:
                found_all_sensors = False
                print(
                    "'%s' sensor is not seen in %s node server." % (
                        sensor, manufacturer))
        else:
            raise Exception("ERROR: %s" % res_err.decode())
    assert found_all_sensors == True

def test_ipmitool_sel_accessibility(args):
    """Check sel list is accessible."""
    sel_command = "ipmitool sel list"
    _, res_err, res_rc = SimpleProcess(sel_command).run()
    if res_rc != 0:
        res_err = res_err.decode()
        assert False, "CMD failure: %s" % res_err


test_list = [
    test_bmc_config,
    test_bmc_firmware_version,
    test_bmc_is_accessible,
    test_chassis_selftest,
    test_sensor_availability,
    test_ipmitool_sel_accessibility
    ]
