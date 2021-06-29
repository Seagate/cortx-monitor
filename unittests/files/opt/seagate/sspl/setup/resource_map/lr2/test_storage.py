import unittest
import json

from unittest.mock import patch

from files.opt.seagate.sspl.setup.resource_map.lr2.storage import StorageMap

from encl_api_response import (
    ENCLOSURE_RESPONSE, ENCLOSURE_SENSORS_RESPONSE, ENCLOSURE_RESPONSE_EMPTY,
    ENCLOSURE_NW_RESPONSE, CONTROLLER_RESPONSE, DRIVE_RESPONSE,
    SAS_PORTS_RESPONSE, FANMODULES_RESPONSE)


class TestStorageMap(unittest.TestCase):
    _storage_map = None

    @classmethod
    def create_storage_obj(cls):
        if cls._storage_map is None:
            cls._storage_map = StorageMap()
        return cls._storage_map

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.lr2.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_platform_sensors(self, encl_response):
        storage_map = self.create_storage_obj()
        encl_response.return_value = json.loads(ENCLOSURE_SENSORS_RESPONSE)['api-response']['sensors']
        resp = storage_map.get_platform_sensors_info()

        # Temperature
        assert resp["temperature"][0]['uid'] == "sensor_temp_ctrl_B.1"
        assert resp["temperature"][0]["health"]["status"] == "OK"
        assert resp["temperature"][0]["health"]["specifics"][0]["value"] == "55 C"

        # Current
        assert resp["current"][0]['uid'] == "sensor_curr_psu_0.1.0"
        assert resp["current"][0]["health"]["status"] == "OK"
        assert resp["current"][0]["health"]["specifics"][0]["value"] == "30.85"

        # Voltage
        assert resp["voltage"][0]['uid'] == "sensor_volt_ctrl_B.0"
        assert resp["voltage"][0]["health"]["status"] == "OK"
        assert resp["voltage"][0]["health"]["specifics"][0]["value"] == "8.13"

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.lr2.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_platform_sensors_empty(self, encl_response):
        storage_map = self.create_storage_obj()
        encl_response.return_value = ENCLOSURE_RESPONSE_EMPTY
        resp = storage_map.get_platform_sensors_info()

        # Temperature
        assert "temperature" not in resp

        # Current
        assert "current" not in resp

        # Voltage
        assert "voltage" not in resp

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.lr2.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_sideplane_expander_info(self, encl_response):
        storage_map = self.create_storage_obj()
        encl_response.return_value = json.loads(
            ENCLOSURE_RESPONSE)['api-response']['enclosures']
        resp = storage_map.get_sideplane_expanders_info()
        assert resp[0]['uid'] == 'sideplane_0.D0.B'
        assert resp[0]['health']['status'] == 'OK'
        assert resp[0]['health']['description'] == \
            'sideplane_0.D0.B is in good health.'

        specifics = resp[0]['health']['specifics']
        assert len(specifics) == 1
        assert specifics[0]['name'] == 'Left Sideplane'
        assert specifics[0]['location'] == 'enclosure 0, drawer 0'
        assert specifics[0]["drawer-id"] == 0

        expanders = specifics[0]['expanders']
        assert expanders[0]["uid"] == "expander_0.D0.B0"
        assert expanders[0]['health']["status"] == "OK"
        assert expanders[0]['health']['description'] == \
            "expander_0.D0.B0 is in good health."

        expander_specifics = expanders[0]['health']['specifics']
        assert expander_specifics[0]["location"] == "Enclosure 0, Drawer 0, Left Sideplane"
        assert expander_specifics[0]["name"] == "Sideplane 24-port Expander 0"
        assert expander_specifics[0]["drawer-id"] == 0

    @patch(("files.opt.seagate.sspl.setup.resource_map.lr2.storage."
            "StorageMap.get_realstor_encl_data"))
    def test_get_nw_ports_info(self, encl_response):
        storage_map = self.create_storage_obj()
        encl_response.return_value = json.loads(ENCLOSURE_NW_RESPONSE)
        resp = storage_map.get_nw_ports_info()
        assert resp[0]['uid'] == 'mgmtport_a'
        assert resp[0]['health']['status'] == 'OK'
        assert resp[0]['health']['description'] == \
            'mgmtport_a is in good health.'
        specifics = resp[0]['health']['specifics'][0]
        assert specifics['ip-address'] == '10.0.0.2'
        assert specifics['link-speed'] == '1000mbps'
        assert specifics['controller'] == 'controller-a'

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.lr2.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_controllers(self, encl_response):
        storage_map = self.create_storage_obj()
        encl_response.return_value = json.loads(
            CONTROLLER_RESPONSE)['api-response']['controllers']
        resp = storage_map.get_controllers_info()
        assert resp[0]['uid'] == 'controller_a'
        assert resp[0]['health']['status'] == 'OK'
        specifics = resp[0]['health']['specifics'][0]
        assert specifics['serial-number'] == 'DHSIFTJ-18253C638B'
        assert specifics['model'] == '3865'
        assert specifics['part-number'] == '81-00000117-00-15'
        assert specifics['disks'] == 84
        assert specifics['fw'] == 'GTS265R18-01'
        assert specifics['virtual-disks'] == 2
        assert specifics['location'] == 'Left'

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.lr2.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_drives(self, encl_response):
        storage_map = self.create_storage_obj()
        encl_response.return_value = json.loads(
            DRIVE_RESPONSE)['api-response']['drives']
        resp = storage_map.get_drives_info()
        assert resp[0]['uid'] == 'disk_00.00'
        assert resp[0]['health']['status'] == 'OK'
        specifics = resp[0]['health']['specifics'][0]
        assert specifics['serial-number'] == 'Z4H099ZE0000R6375N70'
        assert specifics['model'] == 'ST2000NM0034'
        assert specifics['size'] == '2000.3GB'
        assert specifics['temperature'] == '20 C'
        assert specifics['disk-group'] == 'poola'
        assert specifics['storage-pool-name'] == 'poola'
        assert specifics['location'] == '0.0'

    @patch(("files.opt.seagate.sspl.setup.resource_map.lr2.storage."
            "StorageMap.get_realstor_encl_data"))
    def test_get_sas_ports_info(self, encl_response):
        encl_response.return_value = SAS_PORTS_RESPONSE
        storage_map = self.create_storage_obj()
        res = storage_map.get_sas_ports_info()
        assert res[0]['uid'] == "drawer_egress_0.D0.A0"
        assert res[0]['health']['status'] == "OK"
        assert res[0]['health']['description'] == \
            "drawer_egress_0.D0.A0 is in good health."
        specifics = res[0]['health']['specifics'][0]
        assert specifics['sas-port-type'] == "Drawer Port Egress"
        assert specifics['controller'] == "A"

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.lr2.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_fanmodules_info(self, encl_response):
        storage_map = self.create_storage_obj()
        encl_response.return_value = json.loads(
            FANMODULES_RESPONSE
        )['api-response']['fan-modules']
        resp = storage_map.get_fanmodules_info()
        assert resp[0]['uid'] == 'fan_module_0.0'
        assert resp[0]['health']['status'] == 'OK'
        assert resp[0]['health']['description'] == 'FAN is in good health'

        assert len(resp[0]['health']['specifics']) == 2
        assert resp[0]['health']['specifics'][0]["uid"] == "fan_0.fm0.0"
        assert resp[0]['health']['specifics'][0]["location"] == "Enclosure 0, Fan Module 0"
        assert resp[0]['health']['specifics'][0]["status"] == "Up"
        assert resp[0]['health']['specifics'][0]["speed"] == 13800


if __name__ == "__main__":
    unittest.main()
