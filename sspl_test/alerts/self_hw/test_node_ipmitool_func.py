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
MIN_REQUIRED_IPMITOOL_VERSION = "1.8.18"


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
    if not (version_found >= MIN_REQUIRED_IPMITOOL_VERSION):
        print("VERSION MISMATCH WITH IPMITOOL")
        print("Expected: %s" % MIN_REQUIRED_IPMITOOL_VERSION)
        print("Found: %s" % version_found)

test_list = [
    test_ipmitool_version
    ]
