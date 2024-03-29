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

import json
import re

from cortx.utils.process import SimpleProcess
from framework.base.sspl_constants import MDADM_PATH, RaidDataConfig
from framework.utils.conf_utils import (SSPL_CONF, Conf, SYSTEM_INFORMATION,
                                        SYSFS_PATH)


class RAID:

    def __init__(self, raid) -> None:
        """Initialize RAID class."""
        self.raid = raid
        self.id = raid.split('/')[-1]

    def get_devices(self):
        output, err, returncode = SimpleProcess(f"mdadm --detail --test {self.raid}").run()
        output = (output + err).decode()
        devices = []
        for state in re.findall(r"^\s*\d+\s*\d+\s*\d+\s*\d+\s*(.*)", output, re.MULTILINE):
            device = {}
            device["state"] = state
            device["identity"] = {}
            path = re.findall(r"\/dev\/(.*)", state)
            if path:
                device["identity"]["path"] = f"/dev/{path[0]}"
                output, _, returncode = SimpleProcess(f'smartctl -i {device["identity"]["path"]} --json').run()
                if returncode == 0:
                    output = json.loads(output)
                    try:
                        device["identity"]["serialNumber"] = output["serial_number"]
                    except KeyError:
                        device["identity"]["serialNumber"] = "None"
                else:
                    device["identity"]["serialNumber"] = "None"
            devices.append(device)
        return devices

    def get_health(self):
        _, _, returncode = SimpleProcess(f"mdadm --detail --test {self.raid}").run()
        if returncode == 0:
            return ("OK", "The array is in good health")
        elif returncode == 2:
            return ("Fault", "The array has multiple failed devices such that it is unusable.")
        elif returncode == 1:
            return ("Degraded", "The array has at least one failed device.")
        else:
            return ("Fault", "There was an error while trying to get information about the array.")

    def get_data_integrity_status(self):
        status = {
                    "raid_integrity_error": "NA",
                    "raid_integrity_mismatch_count": "NA"
                }
        try:
            sysfs = Conf.get(SSPL_CONF, f'{SYSTEM_INFORMATION}>{SYSFS_PATH}')
            with open(f"/{sysfs}/block/{self.id}/{RaidDataConfig.MISMATCH_COUNT_FILE.value}") as f:
                mismatch_count = f.read().strip("\n")
                status["raid_integrity_error"] = mismatch_count != "0"
                status["raid_integrity_mismatch_count"] = mismatch_count
                return status
        except Exception:
            return status


class RAIDs:

    @classmethod
    def get_configured_raids(self):
        try:
            with open(MDADM_PATH) as f:
                mdadm = f.read()
            return [RAID(re.sub(r"\/(?=\d)", "", device.groups()[0])) for device in re.finditer(r"ARRAY\s*(\S*)", mdadm)]
        except Exception:
            return []
