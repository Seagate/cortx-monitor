#!/usr/bin/env python3

# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import os
import json
import shlex

from cortx.utils.process import SimpleProcess


class DriveUtils:
    """Base class for drive related utility functions."""
    def extract_smart_data(self):
        """Extract drive data using smartctl."""
        response = []
        lsscsi_cmd = " ".join(["lsscsi", "|", "grep", "disk"])
        lsscsi_cmd = shlex.split(lsscsi_cmd)
        lsscsi_response, _, _ = SimpleProcess(lsscsi_cmd).run(shell=True)
        os.makedirs(self.boot_drvs_dta, exist_ok=True)
        for res in lsscsi_response.split("\n"):
            drive_path = res.strip().split(' ')[-1]
            smartctl_cmd = f"sudo smartctl -a {drive_path} --json"
            output, _, _ = SimpleProcess(smartctl_cmd).run(shell=True)
            output = json.loads(output)
            output["drive_path"] = drive_path
            response.append(output)
        return response
