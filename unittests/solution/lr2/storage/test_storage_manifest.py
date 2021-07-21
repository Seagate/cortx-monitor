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

import unittest
import json
from unittest.mock import patch, Mock
from solution.lr2.storage.manifest import StorageManifest
from encl_api_response import (ENCLOSURE_RESPONSE, CONTROLLER_RESPONSE,
    DRIVE_RESPONSE, PSU_RESPONSE, FAN_MODULE_RESPONSE)


class TestStorageManifest(unittest.TestCase):
    _storage_manifest = None

    @classmethod
    @patch(
        "framework.platforms.storage.platform.Platform."
        "validate_storage_type_support", new=Mock(return_value=True)
    )
    def create_storage_manifest_obj(cls):
        if cls._storage_manifest is None:
            cls._storage_manifest = StorageManifest()
        return cls._storage_manifest

    @patch(
        "framework.platforms.realstor.realstor_enclosure.RealStorEnclosure"
        ".get_realstor_encl_data"
    )
    def test_get_enclosures_info(self, encl_response):
        storage_manifest = self.create_storage_manifest_obj()
        encl_response.return_value = json.loads(
            ENCLOSURE_RESPONSE)['api-response']['enclosures']
        resp = storage_manifest.get_enclosures_info()
        assert resp[0]['uid'] == 'enclosure_0'
        assert resp[0]['product'] == 'enclosures'
        assert resp[0]['serial_number'] == 'NA'
        assert resp[0]['part_number'] == 'FRUKA62-01'
        specifics = resp[0]['specifics']
        assert specifics[0]['platform'] == 'Gallium3 NX'
        assert specifics[0]['board_model'] == 'Gallium Raidhead-12G'

    @patch(
        "framework.platforms.realstor.realstor_enclosure.RealStorEnclosure"
        ".get_realstor_encl_data"
    )
    def test_get_sideplane_expander_info(self, encl_response):
        storage_manifest = self.create_storage_manifest_obj()
        encl_response.return_value = json.loads(
            ENCLOSURE_RESPONSE)['api-response']['enclosures']
        resp = storage_manifest.get_sideplane_expander_info()
        assert resp[0]['uid'] == 'sideplane_0.D0.B'
        assert resp[0]['product'] == 'sideplanes'
        specifics = resp[0]['specifics']
        assert len(specifics) == 1
        assert specifics[0]['name'] == 'Left Sideplane'
        assert specifics[0]['location'] == 'enclosure 0, drawer 0'
        assert specifics[0]['drawer_id'] == 0
        expanders = specifics[0]['expanders']
        assert expanders[0]['uid'] == 'expander_0.D0.B0'
        assert expanders[0]['product'] == 'expanders'
        expander_specifics = expanders[0]['specifics']
        assert expander_specifics[0]['location'] == 'Enclosure 0, Drawer 0, Left Sideplane'
        assert expander_specifics[0]['name'] == 'Sideplane 24-port Expander 0'
        assert expander_specifics[0]['drawer_id'] == 0

    @patch(
        "framework.platforms.realstor.realstor_enclosure.RealStorEnclosure"
        ".get_realstor_encl_data"
    )
    def test_get_controllers(self, encl_response):
        storage_manifest = self.create_storage_manifest_obj()
        encl_response.return_value = json.loads(
            CONTROLLER_RESPONSE)['api-response']['controllers']
        resp = storage_manifest.get_controllers_info()
        assert resp[0]['uid'] == 'controller_a'
        assert resp[0]['product'] == 'controllers'
        assert resp[0]['serial_number'] == 'DHSIFTJ-18253C638B'
        assert resp[0]['part_number'] == '81-00000117-00-15'
        specifics = resp[0]['specifics'][0]
        assert specifics['model'] == '3865'
        assert specifics['disks'] == 84
        assert specifics['fw'] == 'GTS265R18-01'
        assert specifics['virtual_disks'] == 2

    @patch(
        "framework.platforms.realstor.realstor_enclosure.RealStorEnclosure"
        ".get_realstor_encl_data"
    )
    def test_get_drives(self, encl_response):
        storage_manifest = self.create_storage_manifest_obj()
        encl_response.return_value = json.loads(
            DRIVE_RESPONSE)['api-response']['drives']
        resp = storage_manifest.get_drives_info()
        assert resp[0]['uid'] == 'disk_00.00'
        assert resp[0]['product'] == 'drive'
        assert resp[0]['serial_number'] == 'Z4H099ZE0000R6375N70'
        specifics = resp[0]['specifics'][0]
        assert specifics['model'] == 'ST2000NM0034'
        assert specifics['size'] == '2000.3GB'
        assert specifics['temperature'] == '20 C'
        assert specifics['location'] == '0.0'

    @patch(
        "framework.platforms.realstor.realstor_enclosure.RealStorEnclosure"
        ".get_realstor_encl_data"
    )
    def get_psu_info(self, encl_response):
        storage_manifest = self.create_storage_manifest_obj()
        encl_response.return_value = json.loads(
            PSU_RESPONSE)['api-response']['controllers']
        resp = storage_manifest.get_psu_info()
        assert resp[0]['uid'] == 'psu_0.0'
        assert resp[0]['product'] == 'power-supplies'
        assert resp[0]['serial_number'] == ''
        assert resp[0]['part_number'] == ''
        specifics = resp[0]['specifics'][0]
        assert specifics['location'] == 'Enclosure 0 - Left'
        assert specifics['model'] == ''
        assert specifics['status'] == 'Up'

    @patch(
        "framework.platforms.realstor.realstor_enclosure.RealStorEnclosure"
        ".get_realstor_encl_data"
    )
    def test_get_fan_modules_info(self, encl_response):
        storage_manifest = self.create_storage_manifest_obj()
        encl_response.return_value = json.loads(
            FAN_MODULE_RESPONSE)['api-response']['fan-modules']
        resp = storage_manifest.get_fan_modules_info()
        assert resp[0]['uid'] == 'fan_module_0.0'
        assert resp[0]['product'] == 'fan-modules'
        specifics = resp[0]['specifics']
        assert specifics[0]['uid'] == 'fan_0.fm0.0'
        assert specifics[0]['product'] == 'fan-details'
        fans = specifics[0]['specifics']
        assert fans[0]['status'] == 'Up'
        assert fans[0]['speed'] == 13800
        assert fans[0]['location'] == 'Enclosure 0, Fan Module 0'


if __name__ == "__main__":
    unittest.main()
