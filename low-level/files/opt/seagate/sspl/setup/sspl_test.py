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

from cortx.sspl.bin.sspl_constants import PRODUCT_FAMILY
from cortx.utils.process import SimpleProcess
from cortx.utils.validator.v_pkg import PkgV
from cortx.sspl.bin.error import SetupError

TEST_DIR = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/sspl_test"

class SSPLTestCmd:
    """Starts test based on plan (sanity|alerts|self_primary|self_secondary)."""

    def __init__(self, args: list):
        self.args = args
        self.name = "sspl_test"
        self.plan = "self_primary"
        self.avoid_rmq = False

    def process(self):
        for arg in self.args:
            try:
                if arg == "--plan":
                    arg_index = self.args.index("--plan")
                    self.plan = self.args[arg_index + 1]
                elif arg == "--avoid_rmq":
                    self.avoid_rmq = True
            except:
                continue
        # TODO: Convert shell script to python
        # from cortx.sspl.sspl_test.run_qa_test import RunQATest
        # RunQATest(self.plan, self.avoid_rmq).run()
        CMD = "%s/run_qa_test.sh %s %s" % (TEST_DIR, self.plan, self.avoid_rmq)
        output, error, returncode = SimpleProcess(CMD).run(realtime_output=True)
        if returncode != 0:
            raise SetupError(returncode, error + " CMD: %s", CMD)
