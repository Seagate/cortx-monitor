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

import json
import shlex
from cortx.utils.process import PipedProcess, SimpleProcess


class DriveUtils:
    """Base class for drive related utility functions."""

    @staticmethod
    def get_smart_data():
        """Extract drive SMART test data using smartctl."""
        response = []
        lsscsi_cmd = "lsscsi | grep disk"
        lsscsi_response, _, _ = PipedProcess(lsscsi_cmd).run()
        lsscsi_response = lsscsi_response.decode()
        for res in lsscsi_response.split("\n"):
            drive_path = res.strip().split(' ')[-1]
            if drive_path not in ["", "-"]:
                smartctl_cmd = " ".join(
                        ["smartctl", "-a", drive_path, "--json"])
                smartctl_cmd = shlex.split(smartctl_cmd)
                smartctl_response, _, _ = SimpleProcess(smartctl_cmd).run()
                smartctl_response = json.loads(smartctl_response)
                smartctl_response["drive_path"] = drive_path
                response.append(smartctl_response)
        return response
