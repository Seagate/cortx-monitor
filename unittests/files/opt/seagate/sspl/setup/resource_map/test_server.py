import unittest

from unittest.mock import patch

from files.opt.seagate.sspl.setup.resource_map.server import ServerMap


def get_sdr_type_response(cmd):
    if cmd == "sdr type 'Temperature'":
        return (
            (
                b"""CPU1 Temp        | 01h | ok  |  3.1 | 36 degrees C
                    CPU2 Temp        | 02h | ok  |  3.2 | 38 degrees C
                    PCH Temp         | 0Ah | ok  |  7.1 | 50 degrees C""",
            ),
            0,
        )

    if cmd == "sdr type 'Voltage'":
        return (
            (
                b"""12V              | 30h | ok  |  7.32 | 12.37 Volts
                    5VCC             | 31h | ok  |  7.33 | 5 Volts
                    3.3VCC           | 32h | ok  |  7.34 | 3.37 Volts""",
            ),
            0,
        )

    if cmd == "sdr type 'Current'":
        return (b"",), 0


class TestStorageMap(unittest.TestCase):
    def setUp(self) -> None:
        self.server_map = ServerMap()

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_platform_sensor_data_temperature(self, sdr_type):
        sdr_type.side_effect = get_sdr_type_response
        resp = self.server_map.build_platform_sensor_data()
        assert resp["Temperature"][0]["uid"] == "CPU1_Temp"
        assert resp["Temperature"][0]["health"]["status"] == "ok"
        assert (
            resp["Temperature"][0]["health"]["description"]
            == "CPU1_Temp is in good health"
        )
        assert (
            resp["Temperature"][0]["health"]["specifics"][0]["Sensor Reading"]
            == "36 degrees C"
        )

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_platform_sensor_voltage(self, sdr_type):
        sdr_type.side_effect = get_sdr_type_response
        resp = self.server_map.build_platform_sensor_data()
        assert resp["Voltage"][0]["uid"] == "12V"
        assert resp["Voltage"][0]["health"]["status"] == "ok"
        assert resp["Voltage"][0]["health"]["description"] == "12V is in good health"
        assert (
            resp["Voltage"][0]["health"]["specifics"][0]["Sensor Reading"]
            == "12.37 Volts"
        )

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_platform_sensor_data_current(self, sdr_type):
        sdr_type.side_effect = get_sdr_type_response
        resp = self.server_map.build_platform_sensor_data()
        assert resp["Current"] == []


if __name__ == "__main__":
    unittest.main()
