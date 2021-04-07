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


class Iem:
    Severity = {
    "INFO" : "I", "WARN" : "W", "ERROR" : "E", "CRITICAL" : "C" }

    EVENT_CODE = {
    "IPMITOOL_ERROR" : "0050010001",
    "IPMITOOL_UNAVAILABLE" : "0050010002",
    "HDPARM_ERROR" : "0050010003",
    "HDPARM_UNAVAILABLE" : "0050010004",
    "SMARTMONTOOL_ERROR" : "0050010005",
    "UDISKS2_UNAVAILABLE" : "0050010006",
    "KAFKA_NOT_ACTIVE" : "0050020001",
    "KAFKA_ACTIVE" : "0050020002"
    }

    # EVENT_STRING = { event_code : [description, impact, recommendation] }
    EVENT_STRING = {
        "0050010001" : ["Ipmitool command execution error.",
            "Server resource monitoring halted.",
            "Reinstall/reconfigure ipmitool package."],
        "0050010002" : ["Ipmitool is not installed.",
            "Server sensors can not be monitored.",
            "Install ipmitool package."],
        "0050010003" : ["Hdparm command execution error.",
            "Server local drives can not be monitored.",
            "Reinstall/reconfigure hdparm package."],
        "0050010004" : ["Hdparm is not installed.",
            "Server local drives can not be monitored.",
            "Install hdparm package."],
        "0050010005" : ["Smartctl command execution error.",
            "Can not fetch drive information.",
            "Reinstall/reconfigure smartmonotool package."],
        "0050010006" : ["UDISKS2 is not installed.",
            "Can not fetch drive information using dbus interface.",
            "Reinstall/reconfigure udisks2 package."],
        "0050020001" : ["Kafka service is not in active state.",
            "SSPL can not raise an alerts.",
            "Reconfigure/start kafka service."],
        "0050020002" : ["Kafka service is in active state.",
            "Kafka service is available.",
            ""]
    }

    def generate_iem(self, severity, event_code, desc):
        iem = "IEC:%sS%s:%s" %(severity, event_code, desc)
        self.log_iem(iem)

    def log_iem(self, iem):
        syslog.syslog(iem)