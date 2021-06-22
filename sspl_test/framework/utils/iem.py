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

from framework.base.sspl_constants import IEM_DATA_PATH
from framework.utils.service_logging import logger
from cortx.utils.iem_framework import EventMessage
from cortx.utils.iem_framework.error import EventMessageError


class Iem:
    # event_name will be added in this list in case of fault iem.
    # and before raising fault_resolved iems,
    # will check if event is present in this list or not.
    fault_iems = []
    Severity = {
        "INFO" : "I", "WARN" : "W", "ERROR" : "E", "CRITICAL" : "C" }

    # EVENT_CODE = [event_code, event]
    EVENT_CODE = {
        "IPMITOOL_ERROR" : ["0050010001", "ipmitool"],
        "IPMITOOL_AVAILABLE" : ["0050010002", "ipmitool"],
        "HDPARM_ERROR" : ["0050010003", "hdparm"],
        "HDPARM_AVAILABLE" : ["0050010004", "hdparm"],
        "SMARTCTL_ERROR" : ["0050010005", "smartctl"],
        "SMARTCTL_AVAILABLE" : ["0050010006", "smartctl"],
        "UDISKS2_UNAVAILABLE" : ["0050010007", "udisks2"],
        "UDISKS2_AVAILABLE" : ["0050010008", "udisks2"],
        "KAFKA_NOT_ACTIVE" : ["0050020001", "kafka"],
        "KAFKA_ACTIVE" : ["0050020002", "kafka"]
    }

    # EVENT_STRING = { event_code : [description, impact, recommendation] }
    EVENT_STRING = {
        "0050010001" : ["ipmitool command execution error.",
            "Server resource monitoring through IPMI halted.",
            "Reinstall/reconfigure ipmitool package."],
        "0050010002" : ["ipmitool command execution success again.",
            "Server resource monitoring through IPMI enabled again.",
            ""],
        "0050010003" : ["hdparm command execution error.",
            "Server local drives monitoring through hdparm halted.",
            "Reinstall/reconfigure hdparm package."],
        "0050010004" : ["hdparm command execution success again.",
            "Server local drives monitoring through hdparm enabled again.",
            ""],
        "0050010005" : ["smartctl command execution error.",
            "Unable to fetch server drive SMART test results and related health info.",
            "Reinstall/reconfigure smartmonotools package."],
        "0050010006" : ["smartctl command execution success again.",
            "Enabled again to fetch server drive SMART test results and related health info.",
            ""],
        "0050010007" : ["udisks2 is not installed.",
            "Unable to fetch server drive info using systemd dbus interface.",
            "Reinstall/reconfigure udisks2 package."],
        "0050010008" : ["udisks2 is available.",
            "Enabled again to fetch server drive info using systemd dbus interface.",
            ""],
        "0050020001" : ["Kafka service is not in active state.",
            "Cortx health alerts may not be delivered to consumers like CSM.",
            "Reconfigure/start kafka service."],
        "0050020002" : ["Kafka service is back in active state.",
            "Cortx health alerts will get delivered to consumers like CSM.",
            ""]
    }

    def create_iem_fields(self, event, severity, event_type=None):
        event_code = event[0]
        event_name = event[1]
        description = self.EVENT_STRING[event_code][0]
        self.generate_iem(event_name, event_code, severity, description)

    def iem_fault(self, event):
        event = self.EVENT_CODE[event]
        severity = self.Severity["ERROR"]
        self.create_iem_fields(event, severity)

    def iem_fault_resolved(self, fault_res_event):
        severity = self.Severity["INFO"]
        event = self.EVENT_CODE[fault_res_event]
        event_type = "fault_resolved"
        self.create_iem_fields(event, severity, event_type)

    @staticmethod
    def generate_iem(module, event_code, severity, description):
        """Generate iem and send it to a MessgaeBroker."""
        try:
            logger.info(f"Sending IEM alert for module:{module}"
                        f" and event_code:{event_code}")
            EventMessage.send(module=module, event_id=event_code,
                              severity=severity, message_blob=description)
        except EventMessageError as e:
            logger.error("Failed to send IEM alert."
                         f"Error:{e}")
