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

import os
from time import sleep
from cortx.utils.process import SimpleProcess


def kcs_channel_alert(active_bmc_IF_key, active_bmc_IF_value):
    sleep(0.1)
    # disable kcs interface
    SimpleProcess("touch /tmp/kcs_disable").run()


def lan_channel_alert(active_bmc_IF_key, active_bmc_IF_value):
    sleep(0.1)
    # disable lan interface
    SimpleProcess("touch /tmp/lan_disable").run()


def restore_config():
    if os.path.exists("/tmp/lan_disable"):
        SimpleProcess("rm -rf /tmp/lan_disable").run()
        sleep(0.1)
    elif os.path.exists("/tmp/kcs_disable"):
        SimpleProcess("rm -rf /tmp/kcs_disable").run()
        sleep(0.1)
