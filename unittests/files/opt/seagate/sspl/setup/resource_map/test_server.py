import unittest

from unittest.mock import patch

from files.opt.seagate.sspl.setup.resource_map.server import ServerMap


def get_sdr_type_response(cmd):
    if cmd.startswith("sensor get"):
        return (
            """Locating sensor record...
            Sensor ID              : CPU1 Temp (0x1)
            Entity ID             : 3.1
            Sensor Type (Threshold)  : Temperature
            Sensor Reading        : 36 (+/- 0) degrees C
            Status                : ok
            Lower Non-Recoverable : 5.000
            Lower Critical        : 5.000
            Lower Non-Critical    : 10.000
            Upper Non-Critical    : 83.000
            Upper Critical        : 88.000
            Upper Non-Recoverable : 88.000
            Positive Hysteresis   : 2.000
            Negative Hysteresis   : 2.000
            Assertion Events      :
            Assertions Enabled    :""",
            "",
            0,
        )
    if cmd == "sdr type 'Temperature'":
        return (
            """CPU1 Temp        | 01h | ok  |  3.1 | 36 degrees C
                    CPU2 Temp        | 02h | ok  |  3.2 | 38 degrees C
                    PCH Temp         | 0Ah | ok  |  7.1 | 50 degrees C""",
            "",
            0,
        )

    if cmd == "sdr type 'Voltage'":
        return (
            """12V              | 30h | ok  |  7.32 | 12.37 Volts
                    5VCC             | 31h | ok  |  7.33 | 5 Volts
                    3.3VCC           | 32h | ok  |  7.34 | 3.37 Volts""",
            "",
            0,
        )

    if cmd == "sdr type 'Current'":
        return "", "", 0

    if cmd == "sdr type 'Fan'":
        return (
            """ FAN1             | 41h | ok  | 29.1 | 5800 RPM
                FAN2             | 42h | ok  | 29.2 | 5700 RPM
                RSC FAN          | 49h | ns  | 29.9 | No Reading""",
            "",
            0,
        )


class TestStorageMap(unittest.TestCase):
    def setUp(self) -> None:
        self.server_map = ServerMap()

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_platform_sensor_data_temperature(self, sdr_type):
        sdr_type.side_effect = get_sdr_type_response
        resp = self.server_map.get_platform_sensors_info()
        assert resp["Temperature"][0]["uid"] == "CPU1_Temp"
        assert resp["Temperature"][0]["health"]["status"] == "OK"
        assert (
            resp["Temperature"][0]["health"]["description"]
            == "CPU1_Temp sensor is in good health."
        )
        assert (
            resp["Temperature"][0]["health"]["specifics"][0]["Sensor Reading"]
            == "36 degrees C"
        )
        assert (
            resp["Temperature"][0]["health"]["specifics"][0]["lower_critical_threshold"]
            == "5.000"
        )
        assert (
            resp["Temperature"][0]["health"]["specifics"][0]["upper_critical_threshold"]
            == "88.000"
        )

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_platform_sensor_voltage(self, sdr_type):
        sdr_type.side_effect = get_sdr_type_response
        resp = self.server_map.get_platform_sensors_info()
        assert resp["Voltage"][0]["uid"] == "12V"
        assert resp["Voltage"][0]["health"]["status"] == "OK"
        assert resp["Voltage"][0]["health"]["description"] == "12V sensor is in good health."
        assert (
            resp["Voltage"][0]["health"]["specifics"][0]["Sensor Reading"]
            == "12.37 Volts"
        )
        assert (
            resp["Voltage"][0]["health"]["specifics"][0]["lower_critical_threshold"]
            == "5.000"
        )
        assert (
            resp["Voltage"][0]["health"]["specifics"][0]["upper_critical_threshold"]
            == "88.000"
        )

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_platform_sensor_data_current(self, sdr_type):
        sdr_type.side_effect = get_sdr_type_response
        resp = self.server_map.get_platform_sensors_info()
        assert resp["Current"] == []

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_fan_fru(self, sdr_type):
        resp = {}
        sdr_type.side_effect = get_sdr_type_response
        data = self.server_map.get_fans_info()
        resp['Fan'] = data
        assert resp["Fan"][0]["uid"] == "FAN1"
        assert resp["Fan"][0]["health"]["status"] == "OK"
        assert (
            resp["Fan"][0]["health"]["description"]
            == "FAN1 is in good health."
        )
        assert (
            resp["Fan"][0]["health"]["specifics"][0]["Sensor Reading"]
            == "5800 RPM"
        )
        assert (
            resp["Fan"][0]["health"]["specifics"][0]["lower_critical_threshold"]
            == "5.000"
        )
        assert (
            resp["Fan"][0]["health"]["specifics"][0]["upper_critical_threshold"]
            == "88.000"
        )
        assert resp["Fan"][2]["uid"] == "RSC FAN"
        assert resp["Fan"][2]["health"]["status"] == "NA"
        assert (
            resp["Fan"][2]["health"]["description"]
            == "RSC FAN is not in good health."
        )
        assert (
            resp["Fan"][2]["health"]["recommendation"]
            == "Please Contact Seagate Support."
        )


if __name__ == "__main__":
    unittest.main()
