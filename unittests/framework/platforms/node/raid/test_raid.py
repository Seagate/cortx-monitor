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
import os
import sys
import unittest
from unittest.mock import Mock, mock_open, patch

PROJECT_ROOT = "/".join(os.path.abspath(__file__).split("/")
                        [:-6]) + "/low-level"
sys.path.append(PROJECT_ROOT)
from framework.platforms.server.raid.raid import RAIDs, RAID

with open(f'{os.path.dirname(__file__)}/mdadm.txt', 'rb') as f:
    mdadm = f.read()

simpleprocess_return = [(mdadm, b'', 0),
                        (json.dumps({"serial_number": "ZBS1VV3D"}), b'', 0),
                        (json.dumps({"serial_number": "ZC236QHZ"}), b'', 0)]


class TestRAIDs(unittest.TestCase):

    def setUp(self):
        pass

    def test_get_configured_raid(self):
        with open(f'{os.path.dirname(__file__)}/mdadm.conf') as f:
            mdadm = f.read()
        with patch('framework.platforms.server.raid.raid.open', mock_open(read_data=mdadm)):
            devices = RAIDs.get_configured_raids()
        for device in devices:
            self.assertIsInstance(device, RAID)
        self.assertEqual(devices[0].raid, "/dev/md0")
        self.assertEqual(devices[1].raid, "/dev/md1")


class TestRAID(unittest.TestCase):

    def setUp(self):
        self.raid = RAID("/dev/md0")

    @patch('cortx.utils.process.SimpleProcess.run', Mock(side_effect=simpleprocess_return))
    def test_get_devices(self):
        devices = self.raid.get_devices()
        self.assertListEqual([{"state": "active sync   /dev/sda2", "identity": {
              "path": "/dev/sda2",
              "serialNumber": "ZBS1VV3D"
            }},
            {"state": "active sync   /dev/sdb2", "identity": {
              "path": "/dev/sdb2",
              "serialNumber": "ZC236QHZ"
            }}], devices)

    @patch('cortx.utils.conf_store.Conf.get', Mock())
    def test_get_data_integrity_status(self):
        mdadm = '0\n'
        with patch('framework.platforms.server.raid.raid.open', mock_open(read_data=mdadm)):
            status = self.raid.get_data_integrity_status()
            self.assertEqual(status["raid_integrity_error"], False)
            self.assertEqual(status["raid_integrity_mismatch_count"], "0")

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
