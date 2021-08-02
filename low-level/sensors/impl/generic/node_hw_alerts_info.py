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
        "Drive Present": {
            "Asserted": Alert(
                    "insertion", "informational",
                    "Disk {} is inserted/added.",
                    "None", "None"),
            "Deasserted": Alert(
                    "missing", "critical",
                    "Disk {} is missing/removed.",
                    "Disk {} is not available.",
                    DEFAULT_RECOMMENDATION)
        },
        "Drive Fault": {
            "Asserted": Alert(
                    "fault", "critial",
                    "Disk {} is in bad health.",
                    "Disk {} is not usable.",
                    DEFAULT_RECOMMENDATION),
            "Deasserted": Alert(
                    "fault_resolved", "informational",
                    "Disk {} is now in good helath.",
                    "Disk {} is now usable.", "None")
        }
    }
}
