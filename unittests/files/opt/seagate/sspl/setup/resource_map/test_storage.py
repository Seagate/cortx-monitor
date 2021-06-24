import unittest
import json

from unittest.mock import patch

from files.opt.seagate.sspl.setup.resource_map.storage import StorageMap

from encl_api_response import (
    ENCLOSURE_RESPONSE, ENCLOSURE_SENSORS_RESPONSE, ENCLOSURE_RESPONSE_EMPTY,
    ENCLOSURE_NW_RESPONSE)


class TestStorageMap(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_map = StorageMap()

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_platform_sensors(self, encl_response):
        encl_response.return_value = json.loads(ENCLOSURE_SENSORS_RESPONSE)
        resp = self.storage_map.get_platform_sensors_info()

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
        "files.opt.seagate.sspl.setup.resource_map.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_platform_sensors_empty(self, encl_response):
        encl_response.return_value = ENCLOSURE_RESPONSE_EMPTY
        resp = self.storage_map.get_platform_sensors_info()

        # Temperature
        assert "temperature" not in resp

        # Current
        assert "current" not in resp

        # Voltage
        assert "voltage" not in resp

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_sideplane_expander_info(self, encl_response):
        encl_response.return_value = json.loads(
            ENCLOSURE_RESPONSE)['api-response']['enclosures']
        resp = self.storage_map.get_sideplane_expanders_info()
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

    @patch(("files.opt.seagate.sspl.setup.resource_map.storage."
            "StorageMap.get_realstor_encl_data"))
    def test_get_nw_ports_info(self, encl_response):
        encl_response.return_value = json.loads(ENCLOSURE_NW_RESPONSE)
        resp = self.storage_map.get_nw_ports_info()
        assert resp[0]['uid'] == 'mgmtport_a'
        assert resp[0]['health']['status'] == 'OK'
        assert resp[0]['health']['description'] == \
            'mgmtport_a is in good health.'
        specifics = resp[0]['health']['specifics'][0]
        assert specifics['ip-address'] == '10.0.0.2'
        assert specifics['link-speed'] == '1000mbps'
        assert specifics['controller'] == 'controller-a'


if __name__ == "__main__":
    unittest.main()
