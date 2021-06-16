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
import unittest

from cortx.utils.iem_framework import EventMessage
from cortx.utils.process import SimpleProcess
from framework.utils.iem import Iem


class TestIEM(unittest.TestCase):

    def setUp(self):
        self.module = None
        self.event_code = None
        self.EVENT_CODE = {
        "IPMITOOL_ERROR" : ["0050010001", "ipmitool"],
        "IPMITOOL_AVAILABLE" : ["0050010002", "ipmitool"]
        }
        EventMessage.init(component='sspl', source='S')
        self.iem = Iem()
        # Check existing iem alert present in MessageBus
        EventMessage.subscribe(component='sspl')
        while True:
            msg = EventMessage.receive()
            if msg is None:
                break

    def test_iem_fault_alert_receive(self):
        """Test iem 'ipmitool' fault alert receive."""
        print("### TestCase: test_iem_fault_alert_receive\n")
        self.iem.iem_fault("IPMITOOL_ERROR")
        time.sleep(10)
        EventMessage.subscribe(component='sspl')
        fault_alert = EventMessage.receive()
        print(f"IEM Received:{fault_alert}")
        self.assertIs(type(fault_alert), dict)
        self.assertEqual(fault_alert["iem"]["info"]["severity"], "Error")
        self.assertEqual(fault_alert["iem"]["source"]["module"], "ipmitool")
        self.assertEqual(fault_alert["iem"]["contents"]["event"], "0050010001")

    def test_iem_fault_resolved_alert_receive(self):
        """Test iem 'ipmitool' fault_resolved alert receive."""
        print("### TestCase: test_iem_fault_resolved_alert_receive\n")
        self.iem.iem_fault_resolved("IPMITOOL_AVAILABLE")
        time.sleep(15)
        EventMessage.subscribe(component='sspl')
        fault_resolved_alert = EventMessage.receive()
        print(f"IEM Received:{fault_resolved_alert}")
        self.assertIs(type(fault_resolved_alert), dict)
        self.assertEqual(fault_resolved_alert["iem"]["info"]["severity"], "Informational")
        self.assertEqual(fault_resolved_alert["iem"]["source"]["module"], "ipmitool")
        self.assertEqual(fault_resolved_alert["iem"]["contents"]["event"], "0050010002")

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
