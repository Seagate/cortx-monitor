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
                    "Please insert back the missing drive soon.")
        }),
        **dict.fromkeys(["Drive Fault", "Drive Fault ()"], {
            "Asserted": Alert(
                    "fault", "critial",
                    "Disk in slot '{}' is faulty. [{}]",
                    "Disk functioning may get impacted if left unaddressed.",
                    "Please replace the faulty drive with a healthy one."),
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
                "'Power Supply {}' is present. [{}]",
                # Intel/Supermicro: 'Power Supply 1' is present. [PS1 (0x85)]
                "Power Supply Port is being monitored.", "None"),
            "Deasserted": Alert(
                "missing", "critical",
                "'Power Supply {}', is missing. [{}]",
                "Power supply redundancy is affected, if more power " +
                "supplies go down or missing, server may go offline.",
                "Please install the missing Power supply immediately.")
        }),
        **dict.fromkeys(["Predictive failure", "Predictive failure ()"], {
            "Asserted": Alert(
                "fault", "warning",
                "Failure is predicted for 'Power Supply {}'. [{}]",
                "Power Supply Redundancy will be affected. If more power " +
                "supplies go down or missing, server may go offline.",
                "Please replace the faulty Power supply soon."
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "No Failure threat anymore for 'Power Supply {}'. [{}]",
                "Power Supply regained the healthy state.", "None"
            )
        }),
        **dict.fromkeys(["Failure detected", "Failure detected ()"], {
            "Asserted": Alert(
                "fault", "error",
                "Failure detected for 'Power Supply {}'. [{}]",
                "Power Supply Redundancy is affected. If more power " +
                "supplies go down or missing, server may go offline.",
                "Please replace the faulty Power Supply immediately."
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'Power Supply {}' recovered from the failure. [{}]",
                "Power Supply regained the healthy state.", "None"
            )
        }),
        **dict.fromkeys(["Config Error", "Config Error ()"], {
            "Asserted": Alert(
                "fault", "error",
                "'Power Supply {}' has configuration error. [{}]",
                "Power Supply Redundancy is affected. If error is not fixed, "+
                "and other power supplies go down, server may go offline.",
                DEFAULT_RECOMMENDATION
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "Configuration error resolved for 'Power Supply {}'. [{}]",
                "Power Supply regained the healthy state.", "None"
            )
        }),
        **dict.fromkeys(["Power Supply AC lost", "Power Supply AC lost ()"], {
            "Asserted": Alert(
                "fault", "critical",
                "'Power Supply {}' lost the AC supply. [{}]",
                "Power Supply Redundancy is affected. If more power " +
                "supplies go down or missing, server may go offline.",
                "Check power supply cable connectivity. If power cable " +
                "is connected, cable might be faulty, please check & replace."
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'Power Supply {}' regained the AC Supply. [{}]",
                "Power Supply regained the healthy state.", "None"
            )
        }),
        **dict.fromkeys(["Power Supply Inactive",
                         "Power Supply Inactive ()"], {
            "Asserted": Alert(
                "fault", "critical",
                "'Power Supply {}' is inactive. [{}]",
                "Power Supply Redundancy is affected. If more power " +
                "supplies go down or missing, server may go offline.",
                "Try removing Power supply unit & inserting back, and check " +
                "if recovered. If still inactive, PSU may need replacement."
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'Power Supply {}' is active now. [{}]",
                "Power Supply regained the healthy state.", "None"
            )
        })
    },
    "Fan": {
        **dict.fromkeys(["Fully Redundant", "Fully Redundant ()"], {
            "Asserted": Alert(
                "fault_resolved", "informational",
                "'{} Sensor' has recovered from a failure. [{}]",
                "None", "None"),
            "Deasserted": Alert(
                "fault", "critical",
                "'{} Sensor', lost redundancy . [{}]",
                ("Other System Fans may adjust speed to maintain "
                 "optimal server temperature."),
                ("Rectify Fan issue soon. If not sure, contact Seagate Support,"
                 "as persistent problem may impact server availability.")
            )
        }),
        **dict.fromkeys(["Lower Non-Recoverable", "Lower Non-Recoverable ()"], {
            "Asserted": Alert(
                "fault", "critical",
                ("Lower Non-Recoverable threshold breached for '{}'. [{}]."
                "Its outside expected limits"),
                ("Other System Fans may adjust speed to maintain "
                 "optimal server temperature."),
                ("System should recover by itself overtime."
                 "However, If issue persists for long, contact Seagate support")
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'{} Sensor has recovered from the failure'. [{}]",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Lower Critical", "Lower Critical ()"], {
            "Asserted": Alert(
                "fault", "critical",
                ("Lower Critical threshold breached for '{}'. [{}]."
                "Its outside expected limits"),
                ("Other System Fans may adjust speed to maintain "
                 "optimal server temperature."),
                ("System should recover by itself overtime."
                 "However, If issue persists for long, contact Seagate support")
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'{} Sensor' recovered from the failure. [{}]",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Lower Non-Critical", "Lower Non-Critical ()"], {
            "Asserted": Alert(
                "fault", "critical",
                ("Lower Non-Critical threshold breached for '{}'. [{}]."
                "Its outside expected limits"),
                ("Other System Fans may adjust speed to maintain "
                 "optimal server temperature."),
                ("System should recover by itself overtime."
                 "However, If issue persists for long, contact Seagate support")
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'{} Sensor' recovered from the failure. [{}]",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Upper Non-Critical", "Upper Non-Critical ()"], {
            "Asserted": Alert(
                "fault", "critical",
                ("Upper Non-Critical threshold breached for '{}'. [{}]."
                "Its outside expected limits"),
                ("Other System Fans may adjust speed to maintain "
                 "optimal server temperature."),
                ("System should recover by itself overtime."
                 "However, If issue persists for long, contact Seagate support")
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'{} Sensor' recovered from the failure. [{}]",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Upper Critical", "Upper Critical ()"], {
            "Asserted": Alert(
                "fault", "critical",
                ("Upper Critical threshold breached for '{}'. [{}]"
                "Its outside expected limits"),
                ("Other System Fans may adjust speed to maintain "
                 "optimal server temperature."),
                ("System should recover by itself overtime."
                 "However, If issue persists for long, contact Seagate support")
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'{} Sensor' recovered from the failure. [{}]",
                "None", "None"
            )
        }),
        **dict.fromkeys(["Upper Non-Recoverable", "Upper Non-Recoverable ()"], {
            "Asserted": Alert(
                "fault", "critical",
                ("Upper Non-Recoverable threshold breached for '{}'. [{}]"
                 "Its outside expected limits"),
                ("Other System Fans may adjust speed to maintain "
                 "optimal server temperature."),
                ("System should recover by itself overtime."
                 "However, If issue persists for long, contact Seagate support")
            ),
            "Deasserted": Alert(
                "fault_resolved", "informational",
                "'{} Sensor' recovered from the failure. [{}]",
                "None", "None"
            )
        })
    }
}
