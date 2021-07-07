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

"""
 ***************************************************************************
  Description: StorageMap class provides resource map and related information
               like health, manifest, etc,.
 ***************************************************************************
"""


class StorageMap():
    """Provides storage resource related information."""

    name = "storage"

    def __init__(self):
        """Initialize storage."""
        super().__init__()

    @staticmethod
    def get_health_info(rpath):
        """
        Fetch health information for given rpath

        rpath: Resource path to fetch its health
               Examples:
                    node>storage[0]
                    node>storage[0]>fw
                    node>storage[0]>fw>logical_volumes
        """
        from storage_health import StorageHealth
        storage = StorageHealth()
        info = storage.get_health_info(rpath)
        return info

    @staticmethod
    def get_manifest_info(rpath):
        """
        Fetch manifest information for given rpath

        rpath: Resource path to fetch its health
               Examples:
                    node>storage[0]
                    node>storage[0]>hw
                    node>storage[0]>hw>disks
        """
        from storage_manifest import StorageManifest
        storage = StorageManifest()
        info = storage.get_manifest_info(rpath)
        return info
