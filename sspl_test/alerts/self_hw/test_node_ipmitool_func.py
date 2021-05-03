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

import re

from cortx.utils.process import SimpleProcess
from alerts.self_hw.self_hw_utilities import get_manufacturer_name


REQUIRED_IPMITOOL_VERSION = "1.8.18"
MIN_REQUIRED_SEL_VERSION = 2


def init(args):
    pass

def test_ipmitool_version(args):
    """Check for expected ipmitool & IPMI v2 compliant."""
    # Check ipmitool version
    tool_ver_cmd = "ipmitool -V"    # ipmitool version 1.8.18
    version_found = None
    res_op, res_err, res_rc = SimpleProcess(tool_ver_cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"ipmitool version[\s]+([\w.]+)(.*)", res_op)
        if search_res:
            version_found = search_res.groups()[0]
    else:
        raise Exception("ERROR: %s" % res_err.decode())
    if not (version_found >= REQUIRED_IPMITOOL_VERSION):
        print("VERSION MISMATCH WITH IPMITOOL")
        print("Expected: %s" % REQUIRED_IPMITOOL_VERSION)
        print("Found: %s" % version_found)

    # Check IPMI SEL compliance is >= v2
    sel_ver_cmd = "ipmitool sel info"   # Version : 1.5 (v1.5, v2 compliant)
    res_op, res_err, res_rc = SimpleProcess(sel_ver_cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"Version[\s]+:[\s]+([\w.]+)[\s]+\(([\w.,\s]+)\)(.*)", res_op)
        if search_res:
            if not (float(search_res.groups()[0]) >= MIN_REQUIRED_SEL_VERSION) and \
                "v2" not in search_res.groups()[1]:
                # Fail if ipmi complinace is not >= v2
                print("IPMI IS NOT V2 COMPLIANT.")
                print("Minimum required ipmi version: %s" % MIN_REQUIRED_SEL_VERSION)
                print("Found: %s" % search_res.groups()[1])
                assert(False)
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
    assert(found_all_sensors == True)

def test_ipmitool_sel_accessibility(args):
    """Check sel list is accessible."""
    sel_command = "ipmitool sel list"
    res_op, _, res_rc = SimpleProcess(sel_command).run()
    if res_rc != 0:
        res_op = res_op.decode()


test_list = [
    test_ipmitool_version,
    test_sensor_availability,
    test_ipmitool_sel_accessibility
    ]
