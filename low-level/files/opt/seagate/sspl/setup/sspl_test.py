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
from pkg_resources import Requirement, working_set, VersionConflict

from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store import Conf
from cortx.utils.service import DbusServiceHandler
from cortx.utils.validator.v_pkg import PkgV
from .conf_based_sensors_enable import update_sensor_info
from files.opt.seagate.sspl.setup.setup_logger import logger
from framework.utils.utility import Utility
from framework.base import sspl_constants
from framework.base.sspl_constants import (
    PRODUCT_FAMILY, sspl_config_path, sspl_test_file_path,
    sspl_test_config_path, global_config_path, SSPL_CONFIG_INDEX,
    SSPL_TEST_CONFIG_INDEX, IVT_TEST_PLANS, NOT_IMPLEMENTED_TEST_PLANS,
    sspl_testv2_config_path, sspl_testv2_file_path)


SSPL_TEST_GLOBAL_CONFIG = "sspl_test_gc"


class SSPLTestCmd:
    """Starts test based on plan (sanity|alerts|dev_sanity|full|performance|scalability|regression)."""

    def __init__(self, args: list):
        self.args = args
        self.name = "sspl_test"
        self.plan = "sanity"
        self.coverage_enabled = self.args.coverage
        self.test_dir = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/sspl_test"
        if self.args.v2:
            self.test_dir = f"/opt/seagate/{PRODUCT_FAMILY}/sspl/sspl_test/functional_tests"
            sspl_constants.sspl_test_file_path = sspl_testv2_file_path
            sspl_constants.sspl_test_config_path = sspl_testv2_config_path

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
        pip3_packages_dep = {
            "Flask": "1.1.1",
            "coverage": "5.5"
            }
        if not self.coverage_enabled:
            pip3_packages_dep.pop("coverage")

        # Validate pip3 python pkg with required version.
        for pkg, version in pip3_packages_dep.items():
            installed_pkg = None
            uninstalled_pkg = False
            try:
                pkg_req = Requirement.parse(f"{pkg}=={version}")
                installed_pkg = working_set.find(pkg_req)
            except VersionConflict:
                cmd = f'pip3 uninstall -y {pkg}'
                _, err, ret = SimpleProcess(cmd).run()
                if ret:
                    raise TestException(
                        "Failed to uninstall the pip3 pkg: %s(v%s), "
                        "due to an Error: %s" % (pkg, version, err))
                uninstalled_pkg = True
            except Exception as err:
                raise TestException(
                    "Failed at verification of pip3 pkg: %s, "
                    "due to an Error: %s" % (pkg, err))

            if not installed_pkg or uninstalled_pkg:
                cmd = f'pip3 install {pkg}=={version}'
                _, err, ret = SimpleProcess(cmd).run()
                if ret:
                    raise TestException(
                        "Failed to install the pip3 pkg: %s(v%s), "
                        "due to an Error: %s" % (pkg, version, err))
            logger.info(f"Ensured Package Dependency: {pkg}(v{version}).")

        # Validate rpm dependencies
        pkg_validator = PkgV()
        pkg_validator.validate_rpm_pkgs(
            host=socket.getfqdn(), pkgs=rpm_deps, skip_version_check=True)
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

        # if self.plan is other than "self"
        # then only config change and service restart is required.
        if self.plan not in IVT_TEST_PLANS:
            # Take back up of sspl test config
            sspl_test_backup = '/etc/sspl_tests.conf.back'
            shutil.copyfile(sspl_test_file_path, sspl_test_backup)

            # Add global config in sspl_test config and revert the changes once
            # test completes. Global config path in sspl_tests.conf will be
            # referred by sspl_tests later
            sspl_global_config_url = Conf.get(
                SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_copy_url")
            Conf.set(
                SSPL_CONFIG_INDEX, "SYSTEM_INFORMATION>global_config_copy_url",
                self.sspl_test_gc_copy_url)
            Conf.save(SSPL_CONFIG_INDEX)

            # Enable & disable sensors based on environment
            update_sensor_info(
                SSPL_TEST_CONFIG_INDEX, self.node_type, self.enclosure_type)

            # TODO: Move lines 99-131 & 152-159 to RunQATest class
            # Create dummy service and add service name in /etc/sspl.conf
            service_name = "dummy_service.service"
            service_file_path_src = \
                f"{self.test_dir}/alerts/os/dummy_service_files/dummy_service.service"
            service_executable_code_src = \
                f"{self.test_dir}/alerts/os/dummy_service_files/dummy_service.py"
            service_file_path_des = "/etc/systemd/system"
            service_executable_code_des = "/var/cortx/sspl/test"

            os.makedirs(service_executable_code_des, 0o777, exist_ok=True)

            shutil.copy(service_executable_code_src,
                        f'{service_executable_code_des}/dummy_service.py')
            # Make service file executable.
            cmd = f"chmod +x {service_executable_code_des}/dummy_service.py"
            _, error, returncode = SimpleProcess(cmd).run()
            if returncode != 0:
                logger.error(
                    "%s error occurred while executing cmd: %s"
                    % (error, cmd))
                logger.error(
                    "failed to assign execute permission for"
                    "dummy_service.py. dummy_service will fail.")

            # Copy service file to /etc/systemd/system/ path.
            shutil.copyfile(service_file_path_src,
                            f'{service_file_path_des}/dummy_service.service')
            cmd = "systemctl daemon-reload"
            _, error, returncode = SimpleProcess(cmd).run()
            if returncode != 0:
                logger.error(
                    f"failed to execute '{cmd}',"
                    "systemctl will be unable to manage the"
                    f"dummy_service.service \n Error: {error}")

            self.dbus_service.enable(service_name)
            self.dbus_service.start(service_name)

            service_list = Conf.get(
                SSPL_CONFIG_INDEX, "SERVICEMONITOR>monitored_services")
            service_list.append(service_name)
            Conf.set(
                SSPL_CONFIG_INDEX, "SERVICEMONITOR>monitored_services",
                service_list)

            threshold_inactive_time_original = Conf.get(
                SSPL_CONFIG_INDEX, "SERVICEMONITOR>threshold_inactive_time")
            threshold_inactive_time_new = 30
            Conf.set(
                SSPL_CONFIG_INDEX, "SERVICEMONITOR>threshold_inactive_time",
                threshold_inactive_time_new)
            Conf.save(SSPL_CONFIG_INDEX)

            cpu_usage_alert_wait = Conf.get(
                SSPL_CONFIG_INDEX,
                "NODEDATAMSGHANDLER>high_cpu_usage_wait_threshold")
            memory_usage_alert_wait = Conf.get(
                SSPL_CONFIG_INDEX,
                "NODEDATAMSGHANDLER>high_memory_usage_wait_threshold")

            cpu_usage_alert_wait_new = 10
            memory_usage_alert_wait_new = 20

            Conf.set(
                SSPL_CONFIG_INDEX,
                "NODEDATAMSGHANDLER>high_cpu_usage_wait_threshold",
                cpu_usage_alert_wait_new)
            Conf.set(
                SSPL_CONFIG_INDEX,
                "NODEDATAMSGHANDLER>high_memory_usage_wait_threshold",
                memory_usage_alert_wait_new)
            Conf.save(SSPL_CONFIG_INDEX)

            # TODO: Convert shell script to python
            # from cortx.sspl.sspl_test.run_qa_test import RunQATest
            # RunQATest(self.plan, self.coverage_enabled).run()
            CMD = "%s/run_qa_test.sh --plan %s --coverage %s"\
                % (self.test_dir, self.plan, self.coverage_enabled)
            if self.args.v2:
                CMD = "%s/run_tests.sh --plan %s --coverage %s"\
                   % (self.test_dir, self.plan, self.coverage_enabled)
            try:
                _, error, rc = SimpleProcess(CMD).run(
                    realtime_output=True)
            except KeyboardInterrupt:
                rc = 1
                error = "KeyboardInterrupt occurred while executing sspl test."
                logger.error(
                    "%s - ERROR: %s - CMD %s" % (self.name, error, CMD))
            # Restore the original path/file & service, then throw exception
            # if execution is failed.
            service_list.remove(service_name)
            Conf.set(
                SSPL_CONFIG_INDEX, "SERVICEMONITOR>monitored_services",
                service_list)
            Conf.set(
                SSPL_CONFIG_INDEX,
                "SERVICEMONITOR>threshold_inactive_time",
                threshold_inactive_time_original)
            Conf.set(SSPL_CONFIG_INDEX,
                     "SYSTEM_INFORMATION>global_config_copy_url",
                     sspl_global_config_url)
            Conf.set(SSPL_CONFIG_INDEX,
                     "NODEDATAMSGHANDLER>high_cpu_usage_wait_threshold",
                     cpu_usage_alert_wait)
            Conf.set(SSPL_CONFIG_INDEX,
                     "NODEDATAMSGHANDLER>high_memory_usage_wait_threshold",
                     memory_usage_alert_wait)
            Conf.save(SSPL_CONFIG_INDEX)
            shutil.copyfile(sspl_test_backup, sspl_test_file_path)
            if rc != 0:
                raise TestException(
                    "%s - ERROR: %s - CMD %s" % (self.name, error, CMD))

            print('Restarting the SSPL service..')
            CMD = "systemctl restart sspl-ll"
            try:
                SimpleProcess(CMD).run(realtime_output=True)
            except Exception as error:
                raise TestException(
                    "Error occurred while executing sspl tests: %s" % error)
        elif self.plan in NOT_IMPLEMENTED_TEST_PLANS:
            print("Tests skipped, test plan %s not applicable for SSPL." % (
                self.plan))
            return 0
        else:
            # TODO: Convert shell script to python
            # from cortx.sspl.sspl_test.run_qa_test import RunQATest
            # RunQATest(self.plan).run()
            try:
                CMD = "%s/run_qa_test.sh --plan %s" % (self.test_dir, self.plan)
                if self.args.v2:
                    CMD = "%s/run_tests.sh --plan %s" % (self.test_dir, self.plan)
                _, error, returncode = SimpleProcess(CMD).run(
                    realtime_output=True)
            except KeyboardInterrupt:
                msg = "KeyboardInterrupt occurred while executing sspl test."
                logger.error(msg)
                raise TestException(msg)
            except Exception as error:
                msg = "Error occurred while executing self test: %s" % error
                logger.error(msg)
                raise TestException(msg)


class TestException(Exception):
    def __init__(self, message):
        """Handle error msg from thread modules."""
        self._desc = message

    def __str__(self):
        """Returns formated error msg."""
        return "error: %s" % (self._desc)
