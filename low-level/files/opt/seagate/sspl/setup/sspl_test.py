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
import os
import socket

from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store import Conf
from cortx.utils.service import DbusServiceHandler
from cortx.utils.validator.v_pkg import PkgV
from .conf_based_sensors_enable import update_sensor_info
from framework.utils.utility import Utility
from framework.base.sspl_constants import (PRODUCT_FAMILY, sspl_config_path,
    sspl_test_file_path, sspl_test_config_path, global_config_path,
    GLOBAL_CONFIG_INDEX, SSPL_CONFIG_INDEX, SSPL_TEST_CONFIG_INDEX, SSPL_BASE_DIR)


TEST_DIR = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/sspl_test"
SSPL_TEST_GLOBAL_CONFIG = "sspl_test_gc"

class SSPLTestCmd:
    """Starts test based on plan (sanity|alerts|self_primary|self_secondary)."""

    def __init__(self, args: list):
        self.args = args
        self.name = "sspl_test"
        self.plan = "self"
        self.coverage_enabled = False

        self.dbus_service = DbusServiceHandler()
        if args.config and args.config[0]:
            self.sspl_test_gc_url = args.config[0]
        else:
            self.sspl_test_gc_url = global_config_path
        self.sspl_test_gc_copy_file = "/etc/sspl_test_gc_url.yaml"

    def validate(self):
        """Check for required packages are installed."""
        # RPM dependency
        rpm_deps = {
            "cortx-sspl-test": None
            }
        # python 3rd party package dependency
        pip3_3ps_packages_test = {
            "Flask": "1.1.1"
            }
        pkg_validator = PkgV()
        pkg_validator.validate_pip3_pkgs(host=socket.getfqdn(),
            pkgs=pip3_3ps_packages_test, skip_version_check=False)
        pkg_validator.validate_rpm_pkgs(host=socket.getfqdn(),
            pkgs=rpm_deps, skip_version_check=True)
        # Load global, sspl and test configs
        Conf.load(SSPL_CONFIG_INDEX, sspl_config_path)
        Conf.load(SSPL_TEST_CONFIG_INDEX, sspl_test_config_path)
        # Take copy of supplied config passed to sspl_test and load it
        with open(self.sspl_test_gc_copy_file, "w") as f:
            f.write("")
        self.sspl_test_gc_copy_url = "yaml://%s" % self.sspl_test_gc_copy_file
        Conf.load(SSPL_TEST_GLOBAL_CONFIG, self.sspl_test_gc_copy_url)
        Conf.load("global_config", self.sspl_test_gc_url)
        Conf.copy("global_config", SSPL_TEST_GLOBAL_CONFIG)
        # Validate input configs
        machine_id = Utility.get_machine_id()
        self.node_type = Conf.get(SSPL_TEST_GLOBAL_CONFIG,
            "server_node>%s>type" % machine_id)
        enclosure_id = Conf.get(SSPL_TEST_GLOBAL_CONFIG,
            "server_node>%s>storage>enclosure_id" % machine_id)
        self.enclosure_type = Conf.get(SSPL_TEST_GLOBAL_CONFIG,
            "storage_enclosure>%s>type" % enclosure_id)

    def process(self):
        """Run test using user requested test plan."""
        self.plan = self.args.plan[0]
        self.coverage_enabled = self.args.coverage

        # if self.plan is other than "self"
        # then only config change and service restart is required.
        if self.plan not in ["self", "self_primary", "self_secondary"]:
            # Take back up of sspl test config
            sspl_test_backup = '/etc/sspl_tests.conf.back'
            shutil.copyfile(sspl_test_file_path, sspl_test_backup)

            # Add global config in sspl_test config and revert the changes once test completes.
            # Global config path in sspl_tests.conf will be referred by sspl_tests later
            sspl_global_config_url = Conf.get(SSPL_CONFIG_INDEX,
                "SYSTEM_INFORMATION>global_config_copy_url")
            Conf.set(SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_copy_url",
                self.sspl_test_gc_copy_url)
            Conf.save(SSPL_CONFIG_INDEX)

            # Enable & disable sensors based on environment
            update_sensor_info(SSPL_TEST_CONFIG_INDEX, self.node_type, self.enclosure_type)

            # TODO: Move lines 99-131 & 152-159 to RunQATest class
            # Create dummy service and add service name in /etc/sspl.conf
            service_name = "dummy_service.service"
            service_file_path_src = f"{TEST_DIR}/alerts/os/dummy_service_files/dummy_service.service"
            service_executable_code_src = f"{TEST_DIR}/alerts/os/dummy_service_files/dummy_service.py"
            service_file_path_des = "/etc/systemd/system"
            service_executable_code_des = "/var/cortx/sspl/test"

            os.makedirs(service_executable_code_des, 0o777, exist_ok=True)

            shutil.copy(service_executable_code_src,
                        f'{service_executable_code_des}/dummy_service.py')
            # Make service file executable.
            cmd = f"chmod +x {service_executable_code_des}/dummy_service.py"
            _, error, returncode = SimpleProcess(cmd).run()
            if returncode !=0:
                print("%s error occurred while executing cmd: %s" %(error, cmd))
                print("failed to assign execute permission for dummy_service.py."\
                        " dummy_service will fail.")

            # Copy service file to /etc/systemd/system/ path.
            shutil.copyfile(service_file_path_src,
                            f'{service_file_path_des}/dummy_service.service')
            cmd= "systemctl daemon-reload"
            _, error, returncode = SimpleProcess(cmd).run()
            if returncode !=0:
                    print(f"failed to execute '{cmd}', systemctl will be unable"\
                        f" to manage the dummy_service.service \nError: {error}")

            self.dbus_service.enable(service_name)
            self.dbus_service.start(service_name)

            service_list = Conf.get(SSPL_CONFIG_INDEX, "SERVICEMONITOR>monitored_services")
            service_list.append(service_name)
            Conf.set(SSPL_CONFIG_INDEX, "SERVICEMONITOR>monitored_services",
                service_list)

            threshold_inactive_time_original = Conf.get(SSPL_CONFIG_INDEX,
                                        "SERVICEMONITOR>threshold_inactive_time")
            threshold_inactive_time_new = 30
            Conf.set(SSPL_CONFIG_INDEX, "SERVICEMONITOR>threshold_inactive_time",
                threshold_inactive_time_new)
            Conf.save(SSPL_CONFIG_INDEX)

            # TODO: Convert shell script to python
            # from cortx.sspl.sspl_test.run_qa_test import RunQATest
            # RunQATest(self.plan, self.coverage_enabled).run()
            CMD = "%s/run_qa_test.sh --plan %s --coverage %s"\
                   %(TEST_DIR, self.plan, self.coverage_enabled)
            try:
                output, error, rc = SimpleProcess(CMD).run(realtime_output=True)
            except KeyboardInterrupt:
                rc = 1
                error = "KeyboardInterrupt occurred while executing sspl test."
            # Restore the original path/file & service, then throw exception
            # if execution is failed.
            service_list.remove(service_name)
            Conf.set(SSPL_CONFIG_INDEX,"SERVICEMONITOR>monitored_services",
                service_list)
            Conf.set(SSPL_CONFIG_INDEX, "SERVICEMONITOR>threshold_inactive_time",
                threshold_inactive_time_original)
            Conf.set(SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_copy_url",
                sspl_global_config_url)
            Conf.save(SSPL_CONFIG_INDEX)
            shutil.copyfile(sspl_test_backup, sspl_test_file_path)
            if rc != 0:
                raise TestException("%s - ERROR: %s - CMD %s" % (self.name, error, CMD))
        else:
            # TODO: Convert shell script to python
            # from cortx.sspl.sspl_test.run_qa_test import RunQATest
            # RunQATest(self.plan, self.coverage_enabled).run()
            try:
                CMD = "%s/run_qa_test.sh --plan %s --coverage %s"\
                       %(TEST_DIR, self.plan, self.coverage_enabled)
                output, error, returncode = SimpleProcess(CMD).run(realtime_output=True)
            except KeyboardInterrupt:
                raise TestException("KeyboardInterrupt occurred while executing sspl test.")
            except Exception as error:
                raise TestException("Error occurred while executing self test: %s" %error)

class TestException(Exception):
    def __init__(self, message):
            """Handle error msg from thread modules."""
            self._desc = message

    def __str__(self):
        """Returns formated error msg."""
        return "error: %s" %(self._desc)
