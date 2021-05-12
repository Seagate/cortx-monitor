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


IPMITOOL_VERSION = "ipmitool version"
SEL_VERSION = "Version"
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
            r"%s[\s]+([\w.]+)(.*)" % IPMITOOL_VERSION, res_op)
        if search_res:
            version_found = search_res.groups()[0]
    else:
        raise Exception("ERROR: %s" % res_err.decode())
    if not (version_found >= REQUIRED_IPMITOOL_VERSION):
        print("VERSION MISMATCH WITH IPMITOOL")
        print("Expected: %s" % REQUIRED_IPMITOOL_VERSION)
        print("Found: %s" % version_found)

def test_sel_version(args):
    """Check for expected IPMI v2 compliant."""
    # Check IPMI SEL compliance is >= v2
    sel_ver_cmd = "ipmitool sel info"   # Version : 1.5 (v1.5, v2 compliant)
    res_op, res_err, res_rc = SimpleProcess(sel_ver_cmd).run()
    if res_rc == 0:
        res_op = res_op.decode()
        search_res = re.search(
            r"%s[\s]+:[\s]+([\w.]+)[\s]+\(([\w.,\s]+)\)(.*)" % SEL_VERSION, res_op)
        if search_res:
            if not (float(search_res.groups()[0]) >= MIN_REQUIRED_SEL_VERSION) and \
                "v2" not in search_res.groups()[1]:
                # Fail if ipmi complinace is not >= v2
                print("IPMI IS NOT V2 COMPLIANT.")
                print("Minimum required ipmi version: %s" % MIN_REQUIRED_SEL_VERSION)
                print("Found: %s" % search_res.groups()[1])
                assert False
    else:
        raise Exception("ERROR: %s" % res_err.decode())

test_list = [
    test_ipmitool_version,
    test_sel_version
    ]
