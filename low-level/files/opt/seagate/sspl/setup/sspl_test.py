#!/bin/env python3

# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import os
import errno

from cortx.sspl.bin.sspl_constants import PRODUCT_FAMILY
from cortx.utils.process import SimpleProcess

TEST_DIR = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/sspl_test"

class SSPLTestError(Exception):
    """ Generic Exception with error code and output """

    def __init__(self, rc, message, *args):
        self._rc = rc
        self._desc = message % (args)

    def __str__(self):
        if self._rc == 0: return self._desc
        return "error(%d): %s" %(self._rc, self._desc)


class SSPLTestCmd:
    "Run SSPL Test"

    def __init__(self, args: list):
        self.args = args
        self.name = "sspl_test"
    
    def process(self):
        output=None
        CMD="rpm -qa | grep sspl-test"
        output, error, returncode = SimpleProcess(CMD).run()
        if returncode != 0:
            raise SSPLTestError(returncode, error, CMD)
        CMD = f"{TEST_DIR}/run_tests.sh test {' '.join(self.args)}"
        output, error, returncode = SimpleProcess(CMD).run()
        if returncode != 0:
            raise SSPLTestError(returncode, error, CMD)
