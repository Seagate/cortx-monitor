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
from framework.base.sspl_constants import SSPL_TEST_PATH


def init(args):
    pass

# As part of start_checker, during sspl restart, BMC unreachable alert is monitored
# If alert is found, a file will be created
# Check for that file in sspl_test/
def test_self_hw_bmc_connectivity(args):
    if os.path.exists(f"{SSPL_TEST_PATH}/self_hw_bmc_error.txt"):
        # fail the test
        assert(False)


test_list = [test_self_hw_bmc_connectivity]


