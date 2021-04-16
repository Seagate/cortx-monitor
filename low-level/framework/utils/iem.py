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

import syslog
import os

from framework.base.sspl_constants import IEM_DATA_PATH
from framework.utils.service_logging import logger

class Iem:
    Severity = {
        "INFO" : "I", "WARN" : "W", "ERROR" : "E", "CRITICAL" : "C" }

    # EVENT_CODE = [event_code, event]
    EVENT_CODE = {
        "IPMITOOL_ERROR" : ["0050010001", "IPMITOOL"],
        "IPMITOOL_AVAILABLE" : ["0050010002", "IPMITOOL"],
        "HDPARM_ERROR" : ["0050010003", "HDPARM"],
        "HDPARM_AVAILABLE" : ["0050010004", "HDPARM"],
        "SMARTMONTOOL_ERROR" : ["0050010005", "SMARTMONTOOL"],
        "SMARTMONTOOL_AVAILABLE" : ["0050010006", "SMARTMONTOOL"],
        "UDISKS2_UNAVAILABLE" : ["0050010007", "UDISKS2"],
        "UDISKS2_AVAILABLE" : ["0050010008", "UDISKS2"],
        "KAFKA_NOT_ACTIVE" : ["0050020001", "KAFKA"],
        "KAFKA_ACTIVE" : ["0050020002", "KAFKA"]
    }

    # EVENT_STRING = { event_code : [description, impact, recommendation] }
    EVENT_STRING = {
        "0050010001" : ["Ipmitool command execution error.",
            "Server resource monitoring halted.",
            "Reinstall/reconfigure ipmitool package."],
        "0050010002" : ["Ipmitool command executed successfully.",
            "Server resource monitoring started.",
            ""],
        "0050010003" : ["Hdparm command execution error.",
            "Server local drives can not be monitored.",
            "Reinstall/reconfigure hdparm package."],
        "0050010004" : ["Hdparm command executed susscessfully.",
            "Started server local drives monitoring.",
            ""],
        "0050010005" : ["Smartctl command execution error.",
            "Can not fetch drive information.",
            "Reinstall/reconfigure smartmonotool package."],
        "0050010006" : ["Smartctl command executed successfully.",
            "Can fetch drive information.",
            ""],
        "0050010007" : ["UDisks2 is not installed.",
            "Can not fetch drive information using dbus interface.",
            "Reinstall/reconfigure UDisks2 package."],
        "0050010008" : ["UDisks2 is available.",
            "Can fetch drive information using dbus interface.",
            ""],
        "0050020001" : ["Kafka service is not in active state.",
            "SSPL can not raise an alerts.",
            "Reconfigure/start kafka service."],
        "0050020002" : ["Kafka service is in active state.",
            "Kafka service is available.",
            ""]
    }

    def check_previous_iem_event(self, event_name, event_code):
        """Before logging iem, check if is already present."""
        previous_iem_event = None
        is_iem_exist = False
        if not os.path.exists(IEM_DATA_PATH):
            os.makedirs(IEM_DATA_PATH)
        iem_event_path = f'{IEM_DATA_PATH}/iem_{event_name}'
        if not os.path.exists(iem_event_path):
            with open(iem_event_path, 'w') as f:
                f.write(event_code)
                f.close()
        else:
            with open(iem_event_path, 'r') as f:
                previous_iem_event = f.read().strip()
                if previous_iem_event != event_code:
                    with open(iem_event_path, 'w') as file:
                        file.write(event_code)
                        file.close()
                else:
                    logger.info("%s - IEM already created." %event_code)
                    is_iem_exist = True
                f.close()

        return is_iem_exist

    def check_fault_event(self, event_name, *events):
        """Before logging fault_resolved iem event,
        Check if fault iem event is present for that particular event."""
        fault_iem = False
        iem_event_path = f'{IEM_DATA_PATH}/iem_{event_name}'
        if os.path.exists(iem_event_path):
            with open(iem_event_path, 'r') as f:
                previous_iem_event = f.read().strip()
            if previous_iem_event in events:
                fault_iem = True
        return fault_iem

    def generate_iem(self, severity, event_code, event_name, description):
        """Generate iem."""
        iem = "IEC:%sS%s:%s" %(severity, event_code, description)
        previous_iem = self.check_previous_iem_event(event_name, event_code)
        if not previous_iem:
            log_iem(iem)

    def create_iem_fields(self, event, severity):
        event_code = event[0]
        event_name = event[1]
        description = self.EVENT_STRING[event_code][0]
        self.generate_iem(severity, event_code, event_name, description)

    def iem_fault(self, event):
        event = self.EVENT_CODE[event]
        severity = self.Severity["ERROR"]
        self.create_iem_fields(event, severity)

    def iem_fault_resolved(self, fault_event, fault_res_event):
        fault_events = self.EVENT_CODE[fault_event]
        prev_fault_iem_event = self.check_fault_event(
            fault_events[1], fault_events[0])
        if prev_fault_iem_event:
            severity = self.Severity["INFO"]
            event = self.EVENT_CODE[fault_res_event]
            self.create_iem_fields(event, severity)

def log_iem(iem):
    """Log iem using syslog."""
    syslog.syslog(iem)
