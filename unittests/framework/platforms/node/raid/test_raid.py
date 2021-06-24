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

import os
import sys
import time
import unittest
from unittest.mock import Mock, patch
from cortx.utils.process import SimpleProcess

PROJECT_ROOT = "/".join(os.path.abspath(__file__).split("/")
                        [:-6]) + "/low-level"
sys.path.append(PROJECT_ROOT)
from framework.platforms.node.raid.raid import RaidArray


class TestServiceMonitor(unittest.TestCase):

    def setUp(self):
        self.raid_array = RaidArray()
        mdadm = '# mdadm.conf written out by anaconda\nMAILADDR root\nAUTO +imsm +1.x -all\nARRAY /dev/md/0 level=raid1 num-devices=2 UUID=6c9cbe03:018e1941:5b6fff24:92796749\nARRAY /dev/md/1 level=raid1 num-devices=2 UUID=bcf899b5:17b8cdc9:9ed1e528:5148c4ad\n'
        mdstat = 'Personalities : [raid1] \nmd1 : active raid1 sda3[0] sdb3[1]\n      975318016 blocks super 1.2 [2/2] [UU]\n      bitmap: 3/8 pages [12KB], 65536KB chunk\n\nmd0 : active raid1 sda2[0] sdb2[1]\n      1046528 blocks super 1.2 [2/2] [UU]\n      bitmap: 0/1 pages [0KB], 65536KB chunk\n\nunused devices: <none>\n'
        mdadm_detail = (b'/dev/md0:\n           Version : 1.2\n     Creation Time : Thu Jan 28 10:08:13 2021\n        Raid Level : raid1\n        Array Size : 1046528 (1022.00 MiB 1071.64 MB)\n     Used Dev Size : 1046528 (1022.00 MiB 1071.64 MB)\n      Raid Devices : 2\n     Total Devices : 2\n       Persistence : Superblock is persistent\n\n     Intent Bitmap : Internal\n\n       Update Time : Wed Jun 23 06:57:46 2021\n             State : clean \n    Active Devices : 2\n   Working Devices : 2\n    Failed Devices : 0\n     Spare Devices : 0\n\nConsistency Policy : bitmap\n\n              Name : smc24-m16.colo.seagate.com:0  (local to host smc24-m16.colo.seagate.com)\n              UUID : 6c9cbe03:018e1941:5b6fff24:92796749\n            Events : 211\n\n    Number   Major   Minor   RaidDevice State\n       0       8        2        0      active sync   /dev/sda2\n       1       8       18        1      active sync   /dev/sdb2\n', b'', 0)
        self.raid_array._mdstat = mdstat
        self.raid_array._mdadm = mdadm
        SimpleProcess.run = Mock(return_value=mdadm_detail)


    def test_get_configured_devices(self):
        devices = self.raid_array.get_configured_devices()
        self.assertListEqual(devices, ['/dev/md0', '/dev/md1'])
    
    def test_get_devices_status(self):
        drives = self.raid_array.get_devices_status("/dev/md0")
        self.assertListEqual([{"state": "active sync   /dev/sda2", "identity": {
              "path": "/dev/sda2",
              "serialNumber": "None"
            }},
            {"state": "active sync   /dev/sdb2", "identity": {
              "path": "/dev/sdb2",
              "serialNumber": "None"
            }}], drives)
        
    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
