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
from socket import AF_INET
from unittest.mock import patch, Mock
from collections import namedtuple
from solution.lr2.server.health import ServerHealth

snetio = namedtuple('snetio', ['bytes_sent', 'bytes_recv', 'packets_sent',
                               'packets_recv', 'errin', 'errout', 'dropin',
                               'dropout'])
snicaddr = namedtuple('snicaddr', ['family', 'address', 'netmask', 'broadcast',
                                   'ptp'])

NET_IO_COUNTERS = {
    "lo": snetio(bytes_sent=11451635037, bytes_recv=11451635037,
                 packets_sent=91734257, packets_recv=91734257,
                 errin=0, errout=0, dropin=0,  dropout=0)
    }

NET_IF_ADDRESS = {
    'lo': [
        snicaddr(family=AF_INET, address='127.0.0.1',
                 netmask='255.0.0.0', broadcast=None, ptp=None)
        ]
}


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


class TestServerHealth(unittest.TestCase):
    _server_health = None

    @classmethod
    @patch(
        "framework.platforms.server.platform.Platform."
        "validate_server_type_support", new=Mock(return_value=True)
    )
    def create_server_health_obj(cls):
        if cls._server_health is None:
            cls._server_health = ServerHealth()
        return cls._server_health

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_platform_sensor_data_temperature(self, sdr_type):
        server_map = self.create_server_health_obj()
        sdr_type.side_effect = get_sdr_type_response
        resp = server_map.get_platform_sensors_info()
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
        server_map = self.create_server_health_obj()
        sdr_type.side_effect = get_sdr_type_response
        resp = server_map.get_platform_sensors_info()
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
        server_map = self.create_server_health_obj()
        sdr_type.side_effect = get_sdr_type_response
        resp = server_map.get_platform_sensors_info()
        assert resp["Current"] == []

    @patch("framework.utils.ipmi_client.IPMITool._run_ipmitool_subcommand")
    def test_build_fan_fru(self, sdr_type):
        server_map = self.create_server_health_obj()
        resp = {}
        sdr_type.side_effect = get_sdr_type_response
        data = server_map.get_fans_info()
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
    @patch("framework.platforms.server.sas.SAS.get_port_data")
    @patch("framework.platforms.server.sas.SAS.get_port_list")
    @patch("framework.platforms.server.sas.SAS.get_host_list")
    def test_get_sas_hba_info(self, host_list, port_list, port_data):
        server_map = self.create_server_health_obj()
        host_list.return_value = ['host1']
        port_list.return_value = ['port-1:0']
        port_data.return_value = {
            "port_id": "sas_port-1:0",
            "state": "running",
            "sas_address": "0x500c0fff0a98b000"
        }
        resp = server_map.get_sas_hba_info()
        assert resp[0]['uid'] == "SASHBA-1"
        assert resp[0]['health']['status'] == "OK"
        assert resp[0]['health']['description'] == \
            "SASHBA-1 is in good health."
        specifics = resp[0]['health']['specifics'][0]
        assert specifics['num_ports'] == 1
        port = specifics['ports'][0]
        assert port['port_id'] == "sas_port-1:0"
        assert port['state'] == "running"
        assert port['sas_address'] == "0x500c0fff0a98b000"

    @patch("framework.platforms.server.sas.SAS.get_phy_data")
    @patch("framework.platforms.server.sas.SAS.get_phy_list_for_port")
    @patch("framework.platforms.server.sas.SAS.get_port_list")
    def test_get_sas_ports_info(self, port_list, phy_list, phy_data):
        server_map = self.create_server_health_obj()
        port_list.return_value = ['port-1:0']
        phy_list.return_value = ['phy-1:0']
        phy_data.return_value = {
            "phy_id": "phy-1:8",
            "state": "enabled",
            "negotiated_linkrate": "12.0 Gbit"
        }
        resp = server_map.get_sas_ports_info()
        assert resp[0]['uid'] == "sas_port-1:0"
        assert resp[0]['health']['status'] == "OK"
        assert resp[0]['health']['description'] == \
            "sas_port-1:0 is in good health."
        specifics = resp[0]['health']['specifics'][0]
        assert specifics['num_phys'] == 1
        phy = specifics['phys'][0]
        assert phy['phy_id'] == "phy-1:8"
        assert phy['state'] == "enabled"
        assert phy['negotiated_linkrate'] == "12.0 Gbit"

    @patch("solution.lr2.server.health.ServerHealth.get_nw_status")
    @patch("psutil.net_if_addrs")
    @patch("psutil.net_io_counters")
    def test_get_nw_ports_info(self, io_counter, if_addrs, nw_status):
        server_map = self.create_server_health_obj()
        io_counter.return_value = NET_IO_COUNTERS
        if_addrs.return_value = NET_IF_ADDRESS
        nw_status.return_value = ("UP", "CONNECTED")
        resp = server_map.get_nw_ports_info()
        print(resp)
        assert resp[0]['uid'] == 'lo'
        assert resp[0]['health']['status'] == "OK"
        assert resp[0]['health']['description'] == \
            "Network Interface 'lo' is in good health."
        specifics = resp[0]['health']['specifics'][0]
        assert specifics['nwStatus'] == "UP"
        assert specifics['nwCableConnStatus'] == "CONNECTED"
        assert specifics['networkErrors'] == 0
        assert specifics['droppedPacketsIn'] == 0
        assert specifics['droppedPacketsOut'] == 0
        assert specifics['packetsIn'] == 91734257
        assert specifics['packetsOut'] == 91734257
        assert specifics['trafficIn'] == 11451635037
        assert specifics['trafficOut'] == 11451635037


if __name__ == "__main__":
    unittest.main()
