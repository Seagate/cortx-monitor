# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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


import time

from common import check_sspl_ll_is_running
from cortx.utils.iem_framework import EventMessage
from framework.utils.iem import Iem

def init(args):
    EventMessage.init(component='sspl', source='S')
    # Check existing iem alert present in MessageBus
    EventMessage.subscribe(component='sspl')
    while True:
        msg = EventMessage.receive()
        if msg is None:
            break

def test_iem_alerts(self):
    """Test iem 'ipmitool' fault alert receive."""
    check_sspl_ll_is_running()
    Iem().iem_fault("IPMITOOL_ERROR")
    time.sleep(10)
    EventMessage.subscribe(component='sspl')
    fault_alert = EventMessage.receive()
    print(f"IEM Received:{fault_alert}")

    assert(fault_alert is not None)
    assert(fault_alert["iem"]["info"]["severity"] is not None)
    assert(fault_alert["iem"]["info"]["type"] is not None)
    assert(fault_alert["iem"]["info"]["event_time"] is not None)
    assert(fault_alert["iem"]["source"]["module"] is not None)
    assert(fault_alert["iem"]["contents"]["event"] is not None)



test_list = [test_iem_alerts]

