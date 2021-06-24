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

import re
from cortx.utils.process import SimpleProcess


class RaidArray:
    
    def __init__(self) -> None:
        self._mdstat_file = "/proc/mdstat"
        self._mdadm_conf_file = "/etc/mdadm.conf"
        self._read()

    def _read(self):
        with open(self._mdstat_file) as f:
            self._mdstat = f.read()
        with open(self._mdadm_conf_file) as f:
            self._mdadm = f.read()

    def get_configured_devices(self):
        return [re.sub("\/(?=\d)", "", device.groups()[0]) for device in re.finditer("ARRAY\s*(\S*)", self._mdadm)]

    def get_raid_health(self, raid):
        output, _, returncode = SimpleProcess(f"mdadm --detail --test {raid}").run()
        if returncode == 0:
            return "OK"
        elif returncode == 4:
            return "Missing"
        elif returncode == 2:
            return "Fault"
        elif returncode == 1:
            return "Degraded"

    def get_devices_status(self, raid):
        output, _, returncode = SimpleProcess(f"mdadm --detail --test {raid}").run()
        devices = []
        for state in re.findall("^\s*\d+\s*\d+\s*\d+\s*\d+\s*(.*)", output.decode(), re.MULTILINE):
            device = {}
            device["state"] = state
            device["identity"] = {}
            path = re.findall("\/dev\/(.*)", state)
            if path:
                device["identity"]["path"] = f"/dev/{path[0]}"
                device["identity"]["serialNumber"] = "None"
            devices.append(device)
        return devices


    def get_data_integrity_status(self, raid):
        with open(f"/sys/block/{raid.split('/')[-1]}/md/mismatch_cnt") as f:
            return f.read().strip("\n") == "0"
