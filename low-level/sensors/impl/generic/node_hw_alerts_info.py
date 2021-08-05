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
                    # Disk is inserted in slot '0'. [HDD 0 (0xF1)].
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
    }
}
