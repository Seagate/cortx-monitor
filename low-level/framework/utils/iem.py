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

import json
import os
import psutil

from framework.base.sspl_constants import IEM_DATA_PATH, IEM_INIT_FAILED
from framework.utils.service_logging import logger
from framework.utils.store_queue import StoreQueue
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

    iem_store_queue = StoreQueue()

    def check_existing_iem_event(self, event_name, event_code):
        """Before logging iem, check if is already present."""
        previous_iem_event = None
        iem_exist = False
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
                    iem_exist = True
                f.close()

        return iem_exist

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

    def create_iem_fields(self, event, severity, event_type=None):
        event_code = event[0]
        event_name = event[1]
        description = self.EVENT_STRING[event_code][0]
        if event_type == "fault_resolved" and event_name in self.fault_iems:
            iem_event_path = f'{IEM_DATA_PATH}/iem_{event_name}'
            if os.path.exists(iem_event_path):
                os.remove(iem_event_path)
                self.generate_iem(event_name, event_code, severity, description)
        else:
            previous_iem = self.check_existing_iem_event(event_name, event_code)
            if not previous_iem:
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

    def check_existing_fault_iems(self):
        """Incase of sspl restart or node reboot, Check if
        previous iems fault are present."""
        fault_events = ["IPMITOOL_ERROR", "HDPARM_ERROR",
            "UDISKS2_UNAVAILABLE", "SMARTCTL_ERROR", "KAFKA_NOT_ACTIVE"]
        for event in fault_events:
            event_data = self.EVENT_CODE[event]
            event_name = event_data[1]
            prev_fault_iem_event = self.check_fault_event(
                event_name, event_data[0])
            if prev_fault_iem_event:
                self.fault_iems.append(event_name)

    @staticmethod
    def generate_iem(module, event_code, severity, description):
        """Generate iem and send it to a MessgaeBroker."""

        IEM_msg = json.dumps(
            {"iem": {"module": module, "event_code": event_code,
                "severity": severity, "description": description}})
        try:
            if Iem.iem_store_queue.is_empty():
                logger.info(f"Sending IEM alert for module:{module}"
                            f" and event_code:{event_code}")
                # check if IEM Framework initialized,
                # if not, retry initializing the IEM Frameowork
                if os.path.exists(IEM_INIT_FAILED):
                    with open(IEM_INIT_FAILED, 'r') as f:
                        sspl_pid = f.read()
                    if sspl_pid and psutil.pid_exists(int(sspl_pid)):
                        EventMessage.init(component='sspl', source='S')
                        logger.info("IEM framework initialization completed!!")
                    os.remove(IEM_INIT_FAILED)
                EventMessage.send(module=module, event_id=event_code,
                                severity=severity, message_blob=description)
            else:
                logger.info(
                    "'Accumulated iem queue' is not Empty."
                        " Adding IEM to the end of the queue")
                Iem.iem_store_queue.put(IEM_msg)
        except (EventMessageError, Exception) as e:
            logger.error(f"Failed to send IEM alert. Error:{e}."
                "Adding IEM in accumulated queue.")
            Iem.iem_store_queue.put(IEM_msg)
