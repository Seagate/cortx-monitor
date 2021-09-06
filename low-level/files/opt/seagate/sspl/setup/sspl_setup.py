#!/bin/env python3

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

######################################################################
# SSPL Mini provisioner interfaces for component provisioning
######################################################################

import sys
import errno
import argparse
import inspect
import shutil
import os
import syslog
import time
import pwd
from urllib.parse import urlparse
from cortx.utils.conf_store.error import ConfError

# using cortx package
from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store import Conf
from cortx.utils.validator.v_pkg import PkgV
from cortx.utils.validator.v_service import ServiceV
from cortx.utils.validator.error import VError
from files.opt.seagate.sspl.setup.setup_error import SetupError
from files.opt.seagate.sspl.setup.setup_logger import init_logging, logger
from framework.base.sspl_constants import (
    PRVSNR_CONFIG_INDEX, GLOBAL_CONFIG_INDEX,
    global_config_path, sspl_config_path, TEST_REQ_SERVICE_RESTART)
from framework.base.conf_upgrade import ConfUpgrade


class Cmd:
    """Setup Command."""

    def __init__(self, args: dict):
        self._args = args
        self._script_dir = os.path.dirname(os.path.abspath(__file__))

    @property
    def args(self) -> str:
        return self._args

    @staticmethod
    def usage(prog: str):
        """Print usage instructions."""
        sys.stderr.write(f"""{prog}
            [ -h|--help ]
            [ post_install --config [<global_config_url>] ]
            [ init --config [<global_config_url>] ]
            [ config --config [<global_config_url>] ]
            [ test --config [<global_config_url>] --plan [sanity|alerts|dev_sanity|full|performance|scalability|regression] ]
            [ reset --config [<global_config_url>] ]
            [ join_cluster --nodes [<nodes>] ]
            [ manifest_support_bundle [<id>] [<path>] ]
            [ support_bundle [<id>] [<path>] ]
            [ check ]
            [ cleanup [--pre-factory]]
            \n""")

    @staticmethod
    def get_command(desc: str, argv: dict):
        """Return the Command after parsing the command line."""
        if not argv:
            return
        parser = argparse.ArgumentParser(desc)
        subparsers = parser.add_subparsers()
        cmds = inspect.getmembers(sys.modules[__name__])
        cmds = [(x, y) for x, y in cmds
                if x.endswith("Cmd") and x != "Cmd"]
        for name, cmd in cmds:
            cmd.add_args(subparsers, cmd, name)

        args, unknown = parser.parse_known_args(argv)
        args.args = unknown + args.args
        return args.command(args)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.set_defaults(command=cls)

    def copy_input_config(self, stage=None):
        """Dump input config in required format"""
        # Copy input config in another index
        url_spec = urlparse(global_config_path)
        path = url_spec.path
        store_loc = os.path.dirname(path)
        if not os.path.exists(store_loc):
            os.makedirs(store_loc)
        if not os.path.exists(path) or stage == "post_install":
            with open(path, "w") as f:
                f.write("")
        Conf.load(GLOBAL_CONFIG_INDEX, global_config_path)
        Conf.copy(PRVSNR_CONFIG_INDEX, GLOBAL_CONFIG_INDEX)
        Conf.save(GLOBAL_CONFIG_INDEX)


class PostInstallCmd(Cmd):
    """Performs pre-requisite checks and basic configuration."""

    name = "post_install"

    def __init__(self, args: dict):
        """Initialize post install command"""
        from files.opt.seagate.sspl.setup.sspl_post_install import (
            SSPLPostInstall)
        super().__init__(args)
        self.post_install = SSPLPostInstall()
        logger.info("%s - Init done" % self.name)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[],
                             help='Global config url')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate post install command arguments and given input."""
        if not self.args.config:
            msg = "%s - Argument validation failure. %s" % (
                self.name, "Global config URL is required.")
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        # Validate config inputs
        Conf.load(PRVSNR_CONFIG_INDEX, self.args.config[0])
        self.post_install.validate()
        logger.info("%s - Validation done" % self.name)

    def process(self):
        """Perform SSPL post installation."""
        self.copy_input_config(stage=self.name)
        self.post_install.process()
        logger.info("%s - Process done" % self.name)


class PrepareCmd(Cmd):
    """Configures SSPL after node preperation."""

    name = "prepare"

    def __init__(self, args: dict):
        """Initialize prepare command"""
        from files.opt.seagate.sspl.setup.sspl_prepare import SSPLPrepare
        super().__init__(args)
        self.prepare = SSPLPrepare()
        logger.info("%s - Init done" % self.name)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[],
                             help='Global config url')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate prepare install command arguments and given input."""
        if not self.args.config:
            msg = "%s - Argument validation failure. %s" % (
                self.name, "Global config URL is required.")
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        # Validate config inputs
        Conf.load(PRVSNR_CONFIG_INDEX, self.args.config[0])
        self.prepare.validate()
        logger.info("%s - Validation done" % self.name)

    def process(self):
        """Configure SSPL for prepare stage."""
        self.copy_input_config()
        self.prepare.process()
        logger.info("%s - Process done" % self.name)


class ConfigCmd(Cmd):
    """Configures message bus and sspl sensor monitor state."""

    name = "config"

    def __init__(self, args):
        """Initialize config command."""
        from files.opt.seagate.sspl.setup.sspl_config import SSPLConfig
        super().__init__(args)
        self.sspl_config = SSPLConfig()
        logger.info("%s - Init done" % self.name)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[],
                             help='Global config url')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate config command arguments."""
        if not self.args.config:
            msg = "%s - Argument validation failure. %s" % (
                self.name, "Global config URL is required.")
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        # Validate config inputs
        Conf.load(PRVSNR_CONFIG_INDEX, self.args.config[0])
        self.sspl_config.validate()
        logger.info("%s - validation done" % self.name)

    def process(self):
        """Setup SSPL configuration."""
        self.copy_input_config()
        self.sspl_config.process()
        logger.info("%s - Process done" % self.name)


class InitCmd(Cmd):
    """Configure SSPL post cluster configuration."""

    name = "init"

    def __init__(self, args):
        from files.opt.seagate.sspl.setup.sspl_setup_init import SSPLInit
        super().__init__(args)
        self.sspl_init = SSPLInit()
        logger.info("%s - Init done" % self.name)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[],
                             help='Global config url')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate init command arguments."""
        if not self.args.config:
            msg = "%s - Argument validation failure. %s" % (
                self.name, "Global config is required.")
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        # Validate config inputs
        Conf.load(PRVSNR_CONFIG_INDEX, self.args.config[0])
        self.sspl_init.validate()
        logger.info("%s - validation done" % self.name)

    def process(self):
        """Configure SSPL init."""
        self.copy_input_config()
        self.sspl_init.process()
        logger.info("%s - Process done" % self.name)


class TestCmd(Cmd):
    """Starts test based on plan:
    (alerts|dev_sanity|full|performance|regression|sanity).
    """

    name = "test"
    test_plan_found = False
    sspl_test_plans = [
        "alerts", "dev_sanity", "full", "performance", "regression", "sanity",
        "scalability"]
    # alerts: Contains realstor and node - sensors, actuator test cases,
    # intended to run on VM.
    # dev_sanity: Subset of 'alerts' test plan, intended to run on VM.
    # full, performance, regression, scalability: non implemented IVT test
    # plans.
    # sanity: This is one of the IVT test plan, which contains
    # HW related test cases, intended to run on HW setup.


    def __init__(self, args):
        super().__init__(args)
        logger.info("%s - Init done" % self.name)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[],
                             help='Global config url')
        parsers.add_argument('--plan', nargs='*', default=[],
                             help='Test plan type')
        parsers.add_argument('--coverage', action="store_true",
                             help='Boolean - Enable Code Coverage.')
        parsers.add_argument('--v2', action="store_true",
                             help='Boolean - Run tests with v2 test framework with multi-node support.')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate test command arguments."""
        if not self.args.config:
            msg = "%s - Argument validation failure. %s" % (
                self.name, "Global config is required.")
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        if not self.args.plan:
            msg = "%s - Argument validation failure. Test plan is needed" % (
                self.name)
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        result = PkgV().validate("rpms", "sspl-test")
        if result == -1:
            msg = "'sspl-test' rpm pkg not found."
            logger.error(msg)
            raise SetupError(1, msg)

        # Service restart is required for coverage.
        # Hence it can be enabled only with test plans
        # which are present in TEST_REQ_SERVICE_RESTART list.
        if self.args.coverage and self.args.plan[0] not in TEST_REQ_SERVICE_RESTART:
            msg = "Code coverage can not be enabled for %s test plan." \
                % self.args.plan[0]
            logger.error(msg)
            raise SetupError(
                errno.EINVAL, "%s - Argument validation failure. %s",
                self.name,
                msg)
        logger.info("%s - Validation done" % self.name)

    def process(self):
        """Setup and run SSPL test"""
        from files.opt.seagate.sspl.setup.sspl_test import SSPLTestCmd
        sspl_test = SSPLTestCmd(self.args)
        sspl_test.validate()
        sspl_test.process()
        logger.info("%s - Process done" % self.name)


class SupportBundleCmd(Cmd):
    """Collects SSPL support bundle."""

    name = "support_bundle"
    script = "sspl_bundle_generate"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        args = ' '.join(self._args.args)
        sspl_bundle_generate = "%s/%s %s" % (self._script_dir,
                                             self.script, args)
        _, error, rc = SimpleProcess(sspl_bundle_generate).run(
            realtime_output=True)
        if rc != 0:
            msg = "%s - validation failure. %s" % (self.name, error)
            logger.error(msg)
            raise SetupError(rc, msg)
        logger.info("%s - Process done" % self.name)


class ManifestSupportBundleCmd(Cmd):
    """Collects enclosure, cluster and node information."""

    name = "manifest_support_bundle"
    script = "manifest_support_bundle"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        args = ' '.join(self._args.args)
        manifest_support_bundle = "%s/%s %s" % (self._script_dir,
                                                self.script, args)
        _, error, rc = SimpleProcess(manifest_support_bundle).run(
            realtime_output=True)
        if rc != 0:
            msg = "%s - validation failure. %s" % (self.name, error)
            logger.error(msg)
            raise SetupError(rc, msg)
        logger.info("%s - Process done" % self.name)


class ResetCmd(Cmd):

    """Reset Interface is used to reset Data/MetaData
    and clean log files
    """

    name = "reset"
    script = "sspl_reset"

    def __init__(self, args):
        super().__init__(args)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[],
                             help='Global config url')
        parsers.set_defaults(command=cls)

    def validate(self):
        if not self.args.config:
            msg = "%s - Argument validation failure. %s" % (
                self.name, "Global config is required.")
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)

    def process(self):
        from files.opt.seagate.sspl.setup.sspl_reset import Reset
        Reset().process()
        logger.info("%s - Process done" % self.name)


class CheckCmd(Cmd):
    """Validates configs and environment prepared for SSPL initialization.
    """

    name = "check"

    def __init__(self, args):
        super().__init__(args)

        self.SSPL_CONFIGURED = "/var/cortx/sspl/sspl-configured"
        self.services = []

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        if not os.path.exists(self.SSPL_CONFIGURED):
            error = "SSPL is not configured. Run provisioner scripts in %s" % (
                self._script_dir)
            syslog.openlog(logoption=syslog.LOG_PID,
                           facility=syslog.LOG_LOCAL3)
            syslog.syslog(syslog.LOG_ERR, error)
            logger.error(error)
            raise SetupError(1,
                             "%s - validation failure. %s",
                             self.name,
                             error)
        # Validate required services are running
        retry = 3
        while retry > 0:
            try:
                ServiceV().validate('isrunning', self.services)
            except VError:
                retry -= 1
                time.sleep(5)
            else:
                break
        ServiceV().validate('isrunning', self.services)
        logger.info("%s - Validation done" % self.name)

    def process(self):
        pass


class CleanupCmd(Cmd):
    """Restores the default SSPL configs."""

    name = "cleanup"
    product = None

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Validate config inputs
        from framework.utils.utility import Utility
        Conf.load(GLOBAL_CONFIG_INDEX, global_config_path)
        self.product = Utility.get_config_value(GLOBAL_CONFIG_INDEX,
            "cortx>release>product")
        if self.product is None:
            msg = "%s - validation failure. %s" % (
                self.name,
                "'Product' name is required to restore suitable configs.")
            logger.error(msg)
            raise SetupError(errno.EINVAL, msg)
        logger.info("%s - Validation done" % self.name)

    def process(self):
        """Cleanup sspl config and log files."""
        from files.opt.seagate.sspl.setup.sspl_cleanup import SSPLCleanup
        sspl_cleanup = SSPLCleanup(self.args.args)
        sspl_cleanup.process(self.product)
        logger.info("%s - Process done" % self.name)


class BackupCmd(Cmd):
    """Backup support for SSPL componenet."""

    name = "backup"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        logger.info(f"{self.name} interface not implemented.")


class RestoreCmd(Cmd):
    """Restore support for SSPL componenet."""

    name = "restore"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        logger.info(f"{self.name} interface not implemented.")


class PreUpgradeCmd(Cmd):
    """PreUpgrade support for SSPL component."""

    name = "pre_upgrade"

    def __init__(self, args):
        super().__init__(args)
        self.level = args.args[0]

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        logger.info(f"Nothing to be done for {self.name}.")
        if self.level == 'node':
            # No action needed
            pass
        elif self.level == 'cluster':
            # No action needed
            pass


class PostUpgradeCmd(Cmd):
    """PostUpgrade support for SSPL componenet."""

    name = "post_upgrade"

    def __init__(self, args):
        super().__init__(args)
        self.level = args.args[0]

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):

        if self.level == 'node':
            new_conf_url = 'yaml:///opt/seagate/cortx/sspl/conf/sspl.conf.LR2.yaml'
            merged_conf_url = 'yaml:///opt/seagate/cortx/sspl/tmp/merged.conf'
            # Only proceed if both existing and new config path are present
            for filepath in [sspl_config_path, new_conf_url]:
                if not os.path.exists(filepath.split(":/")[1]):
                    logger.debug("Config not upgraded as existing or new config file is not present.")
                    return
            conf_upgrade = ConfUpgrade(sspl_config_path, new_conf_url,
                                       merged_conf_url)
            try:
                conf_upgrade.create_merged_config()
            except ConfError as e:
                logger.error("%s error seen while upgrading config, existing config retained" % e)
            else:
                conf_upgrade.upgrade_existing_config()
            finally:
                conf_upgrade.remove_merged_config()

        elif self.level == 'cluster':
            # No action needed
            pass


def main(argv: dict):
    try:
        init_logging(console_output=True)
        desc = "SSPL Setup Interface"
        command = Cmd.get_command(desc, argv[1:])
        if not command:
            Cmd.usage(argv[0])
            return errno.EINVAL
        command.validate()
        command.process()

    except Exception as e:
        logger.exception(f"Failed in SSPL Setup Interface. ERROR: {e}")
        Cmd.usage(argv[0])
        return errno.EINVAL


if __name__ == '__main__':
    sys.exit(main(sys.argv))
