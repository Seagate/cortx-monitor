import unittest
import json

from unittest.mock import patch

from files.opt.seagate.sspl.setup.resource_map.storage import StorageMap


ENCLOSURE_SENSORS_RESPONSE = """
    {
        "status_code": 200,
        "api-response": {
        "sensors":[
            {
            "drawer-id-numeric": 255,
            "status": "OK",
            "container": "controllers",
            "enclosure-id": 0,
            "sensor-type": "Temperature",
            "durable-id": "sensor_temp_ctrl_B.1",
            "value": "55 C",
            "object-name": "sensor",
            "controller-id-numeric": 0,
            "container-numeric": 19,
            "controller-id": "B",
            "sensor-type-numeric": 0,
            "sensor-name": "CPU Temperature-Ctlr B",
            "drawer-id": "N/A",
            "status-numeric": 1
            },
            {
            "drawer-id-numeric": 255,
            "status": "OK",
            "container": "controllers",
            "enclosure-id": 0,
            "sensor-type": "Temperature",
            "durable-id": "sensor_temp_ctrl_B.3",
            "value": "28 C",
            "object-name": "sensor",
            "controller-id-numeric": 0,
            "container-numeric": 19,
            "controller-id": "B",
            "sensor-type-numeric": 0,
            "sensor-name": "Capacitor Pack Temperature-Ctlr B",
            "drawer-id": "N/A",
            "status-numeric": 1
            },
            {
            "drawer-id-numeric": 255,
            "status": "OK",
            "container": "controllers",
            "enclosure-id": 0,
            "sensor-type": "Voltage",
            "durable-id": "sensor_volt_ctrl_B.0",
            "value": "8.13",
            "object-name": "sensor",
            "controller-id-numeric": 0,
            "container-numeric": 19,
            "controller-id": "B",
            "sensor-type-numeric": 2,
            "sensor-name": "Capacitor Pack Voltage-Ctlr B",
            "drawer-id": "N/A",
            "status-numeric": 1
            },
            {
            "drawer-id-numeric": 255,
            "status": "OK",
            "container": "controllers",
            "enclosure-id": 0,
            "sensor-type": "Voltage",
            "durable-id": "sensor_volt_ctrl_B.1",
            "value": "2.03",
            "object-name": "sensor",
            "controller-id-numeric": 0,
            "container-numeric": 19,
            "controller-id": "B",
            "sensor-type-numeric": 2,
            "sensor-name": "Capacitor Cell 1 Voltage-Ctlr B",
            "drawer-id": "N/A",
            "status-numeric": 1
            },
            {
            "drawer-id-numeric": 255,
            "status": "OK",
            "container": "power-supplies",
            "enclosure-id": 0,
            "sensor-type": "Current",
            "durable-id": "sensor_curr_psu_0.1.0",
            "value": "30.85",
            "object-name": "sensor",
            "controller-id-numeric": 3,
            "container-numeric": 21,
            "controller-id": "N/A",
            "sensor-type-numeric": 1,
            "sensor-name": "Current 12V Rail Loc: right-PSU",
            "drawer-id": "N/A",
            "status-numeric": 1
            },
            {
            "drawer-id-numeric": 255,
            "status": "OK",
            "container": "power-supplies",
            "enclosure-id": 0,
            "sensor-type": "Current",
            "durable-id": "sensor_curr_psu_0.1.1",
            "value": "0.03",
            "object-name": "sensor",
            "controller-id-numeric": 3,
            "container-numeric": 21,
            "controller-id": "N/A",
            "sensor-type-numeric": 1,
            "sensor-name": "Current 5V Rail Loc: right-PSU",
            "drawer-id": "N/A",
            "status-numeric": 1
            }
        ],
        "status": [
            {
                "object-name": "status",
                "response-type": "Success",
                "response-type-numeric": 0,
                "response": "Command completed successfully. (2019-07-04 04:23:04)",
                "return-code": 0,
                "component-id": "",
                "time-stamp": "2019-07-04 04:23:04",
                "time-stamp-numeric": 1562214184
            }
        ]
    }}
    """

ENCLOSURE_RESPONSE_EMPTY = {}

ENCLOSURE_RESPONSE = """
    {
    "status_code": 200,
    "api-response": {
            "enclosures": [
            {
                "object-name": "enclosures",
                "durable-id": "enclosure_0",
                "enclosure-id": 0,
                "enclosure-wwn": "500C0FF03B98E23C",
                "name": "",
                "type": "Titan",
                "type-numeric": 12,
                "iom-type": "Xyratex5U84Rbod",
                "iom-type-numeric": 4,
                "platform-type": "Gallium3 NX",
                "platform-type-numeric": 8,
                "board-model": "Gallium Raidhead-12G",
                "board-model-numeric": 11,
                "location": "",
                "rack-number": 0,
                "rack-position": 0,
                "number-of-coolings-elements": 10,
                "number-of-disks": 28,
                "number-of-power-supplies": 2,
                "status": "Unknown",
                "status-numeric": 6,
                "extended-status": "00000000",
                "midplane-serial-number": "DHSIHOU-18103B98E2",
                "vendor": "Seagate",
                "model": "SP-3584-GAL3-NX",
                "fru-shortname": "",
                "fru-location": "MID-PLANE SLOT",
                "part-number": "FRUKA62-01",
                "mfg-date": "2018-01-08 10:31:00",
                "mfg-date-numeric": 1515407460,
                "mfg-location": "",
                "description": "N/A",
                "revision": "C",
                "dash-level": "",
                "emp-a-rev": "513E",
                "emp-b-rev": "513E",
                "rows": 3,
                "columns": 14,
                "slots": 84,
                "locator-led": "Off",
                "locator-led-numeric": 0,
                "drive-orientation": "horizontal",
                "drive-orientation-numeric": 1,
                "enclosure-arrangement": "vertical",
                "enclosure-arrangement-numeric": 0,
                "emp-a-busid": "00",
                "emp-a-targetid": "127",
                "emp-b-busid": "01",
                "emp-b-targetid": "127",
                "emp-a": "",
                "emp-a-ch-id-rev": "00:127 513E",
                "emp-b": "",
                "emp-b-ch-id-rev": "01:127 513E",
                "midplane-type": "5U84-12G",
                "midplane-type-numeric": 71,
                "midplane-rev": 0,
                "enclosure-power": "666.78",
                "pcie2-capable": "False",
                "pcie2-capable-numeric": 0,
                "health": "Degraded",
                "health-numeric": 1,
                "health-reason": "Health is not applicable in this situation.",
                "health-recommendation": "- No action is required.",
                "drawers": [
                {
                    "object-name": "drawers",
                    "durable-id": "drawer_0.0",
                    "drawer-id": 0,
                    "drawer-wwn": "0000000000000000",
                    "part-number": "N/A",
                    "name": "Drawer 0",
                    "position": "Top",
                    "position-numeric": 2,
                    "rows": 3,
                    "columns": 14,
                    "slots": 42,
                    "number-of-disks": 14,
                    "emp-a-busid": "N/A",
                    "emp-a-targetid": "N/A",
                    "emp-a-rev": "N/A",
                    "emp-b-busid": "N/A",
                    "emp-b-targetid": "N/A",
                    "emp-b-rev": "N/A",
                    "emp-a": "A",
                    "emp-a-ch-id-rev": "N/A",
                    "emp-b": "B",
                    "emp-b-ch-id-rev": "N/A",
                    "locator-led": "Off",
                    "locator-led-numeric": 0,
                    "status": "OK",
                    "status-numeric": 1,
                    "extended-status": "00000000",
                    "health": "OK",
                    "health-numeric": 0,
                    "health-reason": "",
                    "health-recommendation": "",
                    "sideplanes": [
                    {
                        "object-name": "sideplanes",
                        "durable-id": "sideplane_0.D0.B",
                        "enclosure-id": 0,
                        "drawer-id": 0,
                        "dom-id": 1,
                        "path-id": "B",
                        "path-id-numeric": 0,
                        "name": "Left Sideplane",
                        "location": "enclosure 0, drawer 0",
                        "position": "Right",
                        "position-numeric": 1,
                        "status": "OK",
                        "status-numeric": 1,
                        "extended-status": "00000000",
                        "health": "OK",
                        "health-numeric": 0,
                        "health-reason": "",
                        "health-recommendation": "",
                        "expanders": [
                        {
                            "object-name": "expanders",
                            "durable-id": "expander_0.D0.B0",
                            "enclosure-id": 0,
                            "drawer-id": 0,
                            "dom-id": 0,
                            "path-id": "B",
                            "path-id-numeric": 0,
                            "name": "Sideplane 24-port Expander 0",
                            "location": "Enclosure 0, Drawer 0, Left Sideplane",
                            "status": "OK",
                            "status-numeric": 1,
                            "extended-status": "00000000",
                            "fw-revision": "513e",
                            "health": "OK",
                            "health-numeric": 0,
                            "health-reason": "",
                            "health-recommendation": ""
                        }
                        ]
                    }
                    ]
                }
                ]
            }
            ],
            "status": [
            {
                "object-name": "status",
                "response-type": "Success",
                "response-type-numeric": 0,
                "response": "Command completed successfully. (2021-06-21 10:52:14)",
                "return-code": 0,
                "component-id": "",
                "time-stamp": "2021-06-21 10:52:14",
                "time-stamp-numeric": 1624272734
            }
        ]
    }}
    """


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
            'Sideplane is in good state.'

        specifics = resp[0]['health']['specifics']
        assert len(specifics) == 1
        assert specifics[0]['name'] == 'Left Sideplane'
        assert specifics[0]['location'] == 'enclosure 0, drawer 0'
        assert specifics[0]["drawer-id"] == 0

        expanders = specifics[0]['expanders']
        assert expanders[0]["uid"] == "expander_0.D0.B0"
        assert expanders[0]['health']["status"] == "OK"
        assert expanders[0]['health']['description'] == \
            "Expander is in goot state."

        expander_specifics = expanders[0]['health']['specifics']
        assert expander_specifics[0]["location"] == "Enclosure 0, Drawer 0, Left Sideplane"
        assert expander_specifics[0]["name"] == "Sideplane 24-port Expander 0"
        assert expander_specifics[0]["drawer-id"] == 0

if __name__ == "__main__":
    unittest.main()
