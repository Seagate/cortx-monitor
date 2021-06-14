import unittest
import json

from unittest.mock import patch

from files.opt.seagate.sspl.setup.resource_map.storage import StorageMap


ENCLOSURE_RESPONSE = """
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


class TestStorageMap(unittest.TestCase):
    def setUp(self) -> None:
        self.storage_map = StorageMap()

    @patch(
        "files.opt.seagate.sspl.setup.resource_map.storage.StorageMap.get_realstor_encl_data"
    )
    def test_get_platform_sensors(self, encl_response):
        encl_response.return_value = json.loads(ENCLOSURE_RESPONSE)
        resp = self.storage_map.get_platform_sensors()

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
        resp = self.storage_map.get_platform_sensors()

        # Temperature
        assert resp["temperature"] == "Unable to retrive temperature data"

        # Current
        assert resp["current"] == "Unable to retrive current data"

        # Voltage
        assert resp["voltage"] == "Unable to retrive voltage data"


if __name__ == "__main__":
    unittest.main()
