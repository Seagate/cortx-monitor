# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com.

import shutil

from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store import Conf
from cortx.utils.service import DbusServiceHandler
from cortx.utils.validator.v_pkg import PkgV
from .setup_error import SetupError
from .conf_based_sensors_enable import update_sensor_info
from framework.base.sspl_constants import (PRODUCT_FAMILY,
                                           sspl_config_path,
                                           sspl_test_file_path,
                                           sspl_test_config_path,
                                           GLOBAL_CONFIG_INDEX,
                                           SSPL_CONFIG_INDEX,
                                           SSPL_TEST_CONFIG_INDEX)

TEST_DIR = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/sspl_test"

class SSPLTestCmd:
    """Starts test based on plan (sanity|alerts|self_primary|self_secondary)."""

    def __init__(self, args: list):
        self.args = args
        self.name = "sspl_test"
        self.plan = "self_primary"
        self.avoid_rmq = False
        self.dbus_service = DbusServiceHandler()
        # Load global, sspl and test configs
        Conf.load(SSPL_CONFIG_INDEX, sspl_config_path)
        global_config_url = Conf.get(SSPL_CONFIG_INDEX,
                                     "SYSTEM_INFORMATION>global_config_copy_url")
        Conf.load(GLOBAL_CONFIG_INDEX, global_config_url)
        Conf.load(SSPL_TEST_CONFIG_INDEX, sspl_test_config_path)

    @staticmethod
    def validate():
        """Check for required packages are installed."""
        # python 3rd party package dependency
        pip3_3ps_packages_test = {
            "Flask": "1.1.1"
        }
        pkg_validator = PkgV()
        # TODO: Enable version check once EOS-18332 is implemented at
        # infrastructure level by RE.
        pkg_validator.validate_pip3_pkgs(host=None,
                                         pkgs=pip3_3ps_packages_test,
                                         skip_version_check=True)

    def process(self):
        self.plan = self.args.plan[0]
        self.avoid_rmq = self.args.avoid_rmq

        # Take back up of sspl test config
        sspl_test_backup = '/etc/sspl_tests.conf.back'
        shutil.copyfile(sspl_test_file_path, sspl_test_backup)

        # Add global config in sspl_test config and revert the changes once test completes.
        # Global config path in sspl_tests.conf will be referred by sspl_tests later
        global_config_copy_url = Conf.get(SSPL_CONFIG_INDEX,
                                          "SYSTEM_INFORMATION>global_config_copy_url")
        Conf.copy(GLOBAL_CONFIG_INDEX, SSPL_TEST_CONFIG_INDEX)
        Conf.set(SSPL_CONFIG_INDEX,
                 "SYSTEM_INFORMATION>global_config_copy_url", sspl_test_config_path)
        Conf.save(SSPL_CONFIG_INDEX)

        # Enable & disable sensors based on environment
        update_sensor_info(SSPL_TEST_CONFIG_INDEX)

        # Get rabbitmq values from sspl.conf and update sspl_tests.conf
        rmq_passwd = Conf.get(SSPL_CONFIG_INDEX,
                              "RABBITMQEGRESSPROCESSOR>password")
        Conf.set(SSPL_TEST_CONFIG_INDEX,
                 "RABBITMQEGRESSPROCESSOR>password", rmq_passwd)
        Conf.save(SSPL_TEST_CONFIG_INDEX)

        # TODO: Convert shell script to python
        # from cortx.sspl.sspl_test.run_qa_test import RunQATest
        # RunQATest(self.plan, self.avoid_rmq).run()
        CMD = "%s/run_qa_test.sh %s %s" % (TEST_DIR, self.plan, self.avoid_rmq)
        output, error, returncode = SimpleProcess(CMD).run(realtime_output=True)
        # Restore the original path/file & service, then throw exception
        # if execution is failed.
        Conf.set(SSPL_CONFIG_INDEX,
                 "SYSTEM_INFORMATION>global_config_copy_url", global_config_copy_url)
        Conf.save(SSPL_CONFIG_INDEX)
        shutil.copyfile(sspl_test_backup, sspl_test_file_path)
        self.dbus_service.restart('sspl-ll.service')
        if returncode != 0:
            raise SetupError(returncode, "%s - ERROR: %s - CMD %s", self.name, error, CMD)
