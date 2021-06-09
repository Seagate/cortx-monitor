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
import subprocess

#from cortx.utils.iem_framework import EventMessage

PROJECT_ROOT = "/".join(os.path.abspath(__file__).split("/")
                        [:-2]) + "/low-level"
sys.path.append(PROJECT_ROOT)

class TestIEM(unittest.TestCase):

    def setUp(self):
        self.EVENT_CODE = {
        "IPMITOOL_ERROR" : ["0050010001", "ipmitool"],
        "IPMITOOL_AVAILABLE" : ["0050010002", "ipmitool"]
        }
        EventMessage.init(component='sspl', source='S')

    def mock_impitool_fault(self):
        cmd = "yum remove ipmitool"
        run_command(cmd)
        event = self.EVENT_CODE['IMPITOOL_ERROR']
        self.module = event[1]
        self.event_code = event[0]

    def mock_impitool_fault_resolved(self):
        cmd = "yum install ipmitool"
        run_command(cmd)
        event = self.EVENT_CODE['IPMITOOL_AVAILABLE']
        self.module = event[1]
        self.event_code = event[0]

    def test_iem_impitool_fault_alert_send(self):
        """ Test iem 'impitool' fault alert & send it to MessageBus """
        self.mock_impitool_fault()
        severity = 'E'
        description = "ipmitool command execution error"
        EventMessage.send(module=self.module, event_id=self.event_code,
                              severity=severity, message_blob=description)

    def test_iem_impitool_fault_alert_receive(self):
        """ Test iem 'impitool' fault alert receive """
        EventMessage.subscribe(component='sspl')
        fault_alert = EventMessage.receive()
        self.assertIs(type(alert), dict)
        self.assertEqual(fault_alert["iem"]["info"]["severity"], "Error")
        self.assertEqual(fault_alert["iem"]["source"]["module"], "impitool")
        self.assertEqual(fault_alert["iem"]["contents"]["event"], "0050010001")

    def test_iem_impitool_fault_resolved_alert_send(self):
        """ Test iem 'impitool' fault_resolved alert and
        send it to MessageBus """
        self.mock_impitool_fault_resolved()
        severity = 'I'
        description = "ipmitool command execution success again."
        EventMessage.send(module=self.module, event_id=self.event_code,
                              severity=severity, message_blob=description)

    def test_iem_impitool_fault_resolved_receive(self):
        """ Test iem 'impitool' fault_resolved alert receive """
        ventMessage.subscribe(component='sspl')
        fault_alert = EventMessage.receive()
        self.assertIs(type(alert), dict)
        self.assertEqual(fault_alert["iem"]["info"]["severity"], "Info")
        self.assertEqual(fault_alert["iem"]["source"]["module"], "impitool")
        self.assertEqual(fault_alert["iem"]["contents"]["event"], "0050010002")

    def tearDown(self):
        pass

def run_command(command):
    """Run the command and get the response and error returned"""
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response, error = process.communicate()
    return response.rstrip('\n'), error.rstrip('\n')


if __name__ == "__main__":
    unittest.main()



