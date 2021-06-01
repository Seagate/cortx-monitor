#! /usr/bin/python3

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
import unittest
import shutil
from unittest.mock import Mock

from framework.utils.ipmi_client import IpmiFactory, Conf, store
from framework.base.sspl_constants import DATA_PATH
from conftest import BASE_DIR


class TestIpmiTool(unittest.TestCase):
    """Test IpmiTool over different platform and interface settings."""

    ERR_STR = "\noutput: %s\nerror: %s\nreturn code: %s"

    def setUp(self):
        """Mock the config values and spwan required class objects."""
        self.mocked_values = {
            "BMC_INTERFACE>default": 'system',
            "/var/cortx/sspl/data/server/ACTIVE_BMC_IF_SN01": 'system',
            "ip": '10.0.0.1',
            "user": 'adminBMC',
            "secret": ('gAAAAABgi9l0ZR5tSwBoLvDS4m2c6ps5rFzdo1'
                       '-o_mr43C8HYSw5mRRd63je_2251_QU-XlVhgEe_'
                       'k6lQesrrjFVrKkQ70Yfgg==')
        }
        Conf.get = Mock(side_effect=self.mocked_conf)
        store.get = Mock(side_effect=self.mocked_store)
        self.tool = IpmiFactory().get_implementor('ipmitool')

    def mocked_conf(self, *args, **kwargs):
        key = args[1]
        if key.find('bmc') != -1:
            key = key.split('>')[-1]
        return self.mocked_values.get(key, '')

    def mocked_store(self, *args, **kwargs):
        key = args[0]
        return self.mocked_values.get(key, '')

    def test_ipmi_on_vm_over_kcs(self):
        out, err, retcode = self.tool._run_ipmitool_subcommand('sel info')
        err_str = self.ERR_STR % (out, err, retcode)
        self.assertEqual(retcode, 1, msg=err_str)
        self.assertTrue(self.tool.VM_ERROR in err, msg=err_str)

    # TODO: Needs to be implemented
    # def test_ipmi_over_lan(self):
    #     pass

    def test_ipmisimtool(self):
        # Start ipmisimtool
        sspl_test = os.path.join(BASE_DIR, 'sspl_test')
        print(sspl_test)

        shutil.copy(f"{sspl_test}/ipmi_simulator/ipmisimtool", "/usr/bin")
        with open(f"{DATA_PATH}/server/activate_ipmisimtool", 'a'):
            os.utime(f"{DATA_PATH}/server/activate_ipmisimtool")

        out, err, retcode = \
            self.tool._run_ipmitool_subcommand("sdr type 'Fan'")
        err_str = self.ERR_STR % (out, err, retcode)
        self.assertEqual(retcode, 0, msg=err_str)
        self.assertEqual(err, '', msg=err_str)
        self.assertTrue('Fan' in out, msg=err_str)

        # Stop ipmisimtool
        os.remove('/usr/bin/ipmisimtool')
        os.remove(f"{DATA_PATH}/server/activate_ipmisimtool")

    def tearDown(self):
        pass
