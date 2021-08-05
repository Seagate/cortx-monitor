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

from collections import namedtuple
from framework.base.sspl_constants import DEFAULT_RECOMMENDATION

Alert = namedtuple('AlertInfo',
                   ['type', 'severity', 'description',
                    'impact', 'recommendation'])

alert_for_event = {
    "Drive Slot / Bay": {
        **dict.fromkeys(["Drive Present", "Drive Present ()"], {
            "Asserted": Alert(
                    "insertion", "informational",
                    "Disk is inserted in slot '0'. [{}]",
                    # Disk is inserted in slot '0'. [HDD 0 (0xF1)]. (Intel)
                    # Disk is inserted in slot '0'. [Drive 0 (0xF1)]. (Dell)
                    "None", "None"),
            "Deasserted": Alert(
                    "missing", "critical",
                    "Disk is missing/removed from slot '{}'. [{}]",
                    "Server availability may get impacted if redundant " +
                    "drive goes bad or missing.",
                    DEFAULT_RECOMMENDATION)
        }),
        **dict.fromkeys(["Drive Fault", "Drive Fault ()"], {
            "Asserted": Alert(
                    "fault", "critial",
                    "Disk in slot '{}' is faulty. [{}]",
                    "Disk functioning may get impacted if left unaddressed.",
                    DEFAULT_RECOMMENDATION),
            "Deasserted": Alert(
                    "fault_resolved", "informational",
                    "Disk in slot '{}' has recovered. [{}]",
                    "Disk is in good health now.", "None")
        })
    },
    "Power Supply": {
        **dict.fromkeys(["Presence detected", "Presence detected ()"], {
            "Asserted": Alert(
                "insertion", "informational",
                # "Power Supply Sensor (0xc1) has reported the presence
                #  of Power Supply via 'Port 1'"
                "Power Supply Sensor (0x{}) has reported the presence " +
                "of Power Supply via 'Port {}'.",
                "Power Supply Port is being monitored.", "None"),
            "Deasserted": Alert(
                "missing", "critical",
                "Power Supply Sensor (0x{}) failed to detect the presence " +
                "of Power Supply via 'Port {}'.",
                # Power Supply Sensor (0xc1) failed to detect the presence
                # of Power Supply via 'Port 1'.
                "Power Supply Port monitoring has stopped.",
                DEFAULT_RECOMMENDATION)
        }),
        **dict.fromkeys(["Predictive failure", "Predictive failure ()"], {
            "Asserted": Alert(
                "fault", "warning",
                "Power Supply Sensor (0x{}) has predicted the failure " +
                "of Power Supply via 'Port {}'.",
                # Power Supply Sensor (0xc1) has predicted the failure
                # of Power Supply via 'Port 1'
                "Power Supply might stop if no action taken.",
                DEFAULT_RECOMMENDATION
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                # Power Supply Sensor (0xc1) does not find a threat
                # of failure anymore for Power Supply via 'Port 1'.
                "Power Supply Sensor (0x{}) does not find a threat " +
                "of failure anymore for Power Supply via 'Port {}'.",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Failure detected", "Failure detected ()"], {
            "Asserted": Alert(
                "fault", "error",
                "Power Supply Sensor (0x{}) reports a failure " +
                "of Supply via 'Port {}'.",
                # Power Supply Sensor (0xc1) reports a failure of
                # Supply via 'Port 1'
                "Power Supply is interrupted.,",
                DEFAULT_RECOMMENDATION
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "Power Supply Sensor (0x{}) reports, Supply via " +
                "'Port {}' has recovered from the failure.",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Config Error", "Config Error ()"], {
            "Asserted": Alert(
                "fault", "error",
                "Power Supply Sensor (0x{}) reports, 'Port {}' has a " +
                "Configuration Error.",
                "Power Supply port might produce issues.",
                DEFAULT_RECOMMENDATION
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "Power Supply Sensor (0x{}) reports, 'Port {}' " +
                "does not have Configuration Error anymore.",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Power Supply AC lost", "Power Supply AC lost ()"], {
            "Asserted": Alert(
                "fault", "critical",
                "Power Supply Sensor (0x{}) reports, 'Port {}' has lost " +
                "the AC supply.",
                "AC supply is unvailable throught Port {}",
                DEFAULT_RECOMMENDATION
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "Power Supply Sensor (0x{}) reports, 'Port {}' has regained " +
                "the AC supply.",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Power Supply Inactive",
                         "Power Supply Inactive ()"], {
            "Asserted": Alert(
                "fault", "critical",
                "Power Supply Sensor (0x{}) reports, 'Port {}' is inactive.",
                "No Power Supply via Port {}",
                DEFAULT_RECOMMENDATION
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "Power Supply Sensor {} reports, 'Port {}' is active now.",
                "None", "None"
            )
        })
    }
}
