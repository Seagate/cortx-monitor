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

import os
import sys
import unittest

from cortx.utils.iem_framework import EventMessage
from cortx.utils.process import SimpleProcess

PROJECT_ROOT = "/".join(os.path.abspath(__file__).split("/")
                        [:-2]) + "/low-level"
sys.path.append(PROJECT_ROOT)

class TestIEM(unittest.TestCase):

    def setUp(self):
        self.module = None
        self.event_code = None
        self.EVENT_CODE = {
        "IPMITOOL_ERROR" : ["0050010001", "ipmitool"],
        "IPMITOOL_AVAILABLE" : ["0050010002", "ipmitool"]
        }
        EventMessage.init(component='sspl', source='S')

    def mock_ipmitool_fault(self):
        cmd = 'yum remove ipmitool'
        res, _, _ = SimpleProcess(cmd).run()
        event = self.EVENT_CODE['IPMITOOL_ERROR']
        self.module = event[1]
        self.event_code = event[0]

    def mock_ipmitool_fault_resolved(self):
        cmd = 'yum install ipmitool'
        res, _, _ = SimpleProcess(cmd).run()
        event = self.EVENT_CODE['IPMITOOL_AVAILABLE']
        self.module = event[1]
        self.event_code = event[0]

    def test_01_ipmitool_fault_alert_send(self):
        """ Test iem 'ipmitool' fault alert & send it to MessageBus """

        print("### TestCase: test_01_ipmitool_fault_alert_send\n")
        self.mock_ipmitool_fault()
        severity = 'E'
        description = "ipmitool command execution error"
        EventMessage.send(module=self.module, event_id=self.event_code,
                              severity=severity, message_blob=description)

    def test_02_ipmitool_fault_alert_receive(self):
        """ Test iem 'ipmitool' fault alert receive """

        print("### TestCase: test_02_ipmitool_fault_alert_receive\n")
        EventMessage.subscribe(component='sspl')
        fault_alert = EventMessage.receive()
        print(f"IEM Received:{fault_alert}")
        self.assertIs(type(fault_alert), dict)
        self.assertEqual(fault_alert["iem"]["info"]["severity"], "Error")
        self.assertEqual(fault_alert["iem"]["source"]["module"], "ipmitool")
        self.assertEqual(fault_alert["iem"]["contents"]["event"], "0050010001")

    def test_03_ipmitool_fault_resolved_alert_send(self):
        """ Test iem 'ipmitool' fault_resolved alert and
        send it to MessageBus """

        print("### TestCase: test_03_ipmitool_fault_resolved_alert_send\n")
        self.mock_ipmitool_fault_resolved()
        severity = 'I'
        description = "ipmitool command execution success again."
        EventMessage.send(module=self.module, event_id=self.event_code,
                              severity=severity, message_blob=description)

    def test_04_ipmitool_fault_resolved_receive(self):
        """ Test iem 'ipmitool' fault_resolved alert receive """

        print("### TestCase: test_04_ipmitool_fault_resolved_receive\n")
        EventMessage.subscribe(component='sspl')
        fault_alert = EventMessage.receive()
        print(f"IEM Received:{fault_alert}")
        self.assertIs(type(fault_alert), dict)
        self.assertEqual(fault_alert["iem"]["info"]["severity"], "Informational")
        self.assertEqual(fault_alert["iem"]["source"]["module"], "ipmitool")
        self.assertEqual(fault_alert["iem"]["contents"]["event"], "0050010002")

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()



