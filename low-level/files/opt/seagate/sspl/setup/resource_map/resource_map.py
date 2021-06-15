#!/bin/python3

# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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
# please email opensource@seagate.com or cortx-questions@seagate.com

import time
from abc import ABCMeta, abstractmethod

from framework.base.sspl_constants import DEFAULT_RECOMMENDATION

class ResourceMap(metaclass=ABCMeta):
    """Abstract class for all other resource types."""

    name = "resource"

    def __init__(self):
        """Initialize resource."""
        pass

    @abstractmethod
    def get_health_info(self, rpath):
        """
        Get health information of fru in given resource id.

        rpath: Resource id (Example: hw>disks)
        """
        pass

    def get_data_template(self, uid: str, is_fru: bool):
        """Get the health data template."""
        return {
            "uid": uid,
            "fru": str(is_fru).lower(),
            "last_updated": -1,
            "health": {
                "status": "",
                "description": "",
                "recommendation": "",
                "specifics": []
            }
        }

    def set_health_data(self, obj: dict, status, description=None,
                        recommendation=None):
        """Set the given or default health data as per health status."""
        good_state = (status == "OK")
        if not description:
            description = "%s is %sin good health." % (
                            obj.get("uid"),
                            '' if good_state else 'not ')
        if not recommendation:
            recommendation = 'None' if good_state\
                             else DEFAULT_RECOMMENDATION

        obj["health"].update({
            "status": status,
            "description": description,
            "recommendation": recommendation
        })

        obj["last_updated"] = int(time.time())
