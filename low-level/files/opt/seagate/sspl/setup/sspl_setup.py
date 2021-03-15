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
import traceback
import os
import syslog
import time
from urllib.parse import urlparse

# using cortx package
from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store import Conf
from cortx.utils.service import DbusServiceHandler
from cortx.utils.validator.v_pkg import PkgV
from cortx.utils.validator.v_service import ServiceV
from cortx.utils.validator.error import VError
from files.opt.seagate.sspl.setup.setup_error import SetupError


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
            [ test --config [<global_config_url>] --plan [sanity|alerts|self_primary|self_secondary] ]
            [ reset --config [<global_config_url>] --type [hard|soft] ]
            [ join_cluster --nodes [<nodes>] ]
            [ manifest_support_bundle [<id>] [<path>] ]
            [ support_bundle [<id>] [<path>] ]
            [ check ]
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


class JoinClusterCmd(Cmd):
    """Join nodes in cluster. To join mutiple nodes, use delimeter ","
    between node names. ie.node1,node2
    """

    name = "join_cluster"
    script = "setup_rabbitmq_cluster"

    def __init__(self, args):
        super().__init__(args)
        self.nodes = None

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--nodes', nargs='*', default=[], help='Node names separted by comma')
        parsers.set_defaults(command=cls)

    def validate(self):
        if not self.args.nodes:
            raise SetupError(1,
                             "Validation failure. %s",
                             "join_cluster requires comma separated node names as argument.")
        self.nodes = self.args.nodes[0]

    def process(self):
        from files.opt.seagate.sspl.setup.setup_rabbitmq_cluster import RMQClusterConfiguration
        RMQClusterConfiguration(self.nodes).process()


class PostInstallCmd(Cmd):
    """Prepare the environment for sspl service."""

    name = "post_install"

    def __init__(self, args: dict):
        super().__init__(args)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[], help='Global config url')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate post install command arguments"""
        if not self.args.config:
            raise SetupError(1,
                             "%s - Argument validation failure. %s",
                             self.name,
                             "Global config is required.")

    def process(self):
        """Configure SSPL post installation"""
        from files.opt.seagate.sspl.setup.sspl_post_install import SSPLPostInstall
        post_install = SSPLPostInstall(self.args)
        post_install.validate()
        post_install.process()


class InitCmd(Cmd):
    """Creates data path and checks required role."""

    name = "init"

    def __init__(self, args):
        super().__init__(args)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[], help='Global config url')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate init command arguments"""
        if not self.args.config:
            raise SetupError(
                    errno.EINVAL,
                    "%s - Argument validation failure. Global config is needed",
                    self.name)

    def process(self):
        """Configure SSPL init"""
        from files.opt.seagate.sspl.setup.sspl_setup_init import SSPLInit
        sspl_init = SSPLInit()
        sspl_init.process()


class ConfigCmd(Cmd):
    """Configues SSPL role, logs and sensors needs to be enabled."""

    name = "config"

    def __init__(self, args):
        super().__init__(args)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[], help='Global config url')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate config command arguments"""
        if not self.args.config:
            raise SetupError(1,
                             "%s - Argument validation failure. %s",
                             self.name,
                             "Global config is required.")

    def process(self):
        """Setup SSPL configuration"""
        from files.opt.seagate.sspl.setup.sspl_config import SSPLConfig
        sspl_config = SSPLConfig()
        sspl_config.validate()
        sspl_config.process()

class TestCmd(Cmd):
    """Starts test based on plan:
    (sanity|alerts|self_primary|self_secondary)."""

    name = "test"
    test_plan_found = False
    sspl_test_plans = ["sanity", "alerts", "self_primary", "self_secondary"]

    def __init__(self, args):
        super().__init__(args)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[], help='Global config url')
        parsers.add_argument('--plan', nargs='*', default=[], help='Test plan type')
        parsers.add_argument('--avoid_rmq', action="store_true", help='Boolean - Disable RabbitMQ?')
        parsers.set_defaults(command=cls)

    def validate(self):
        """Validate test command arguments"""
        if not self.args.config:
            raise SetupError(errno.EINVAL,
                             "%s - Argument validation failure. %s",
                             self.name,
                             "Global config is required.")

        if not self.args.plan:
            raise SetupError(
                    errno.EINVAL,
                    "%s - Argument validation failure. Test plan is needed",
                    self.name)

        result = PkgV().validate("rpms", "sspl-test")
        if result == -1:
            raise SetupError(1, "'sspl-test' rpm pkg not found.")

    def process(self):
        """Setup and run SSPL test"""
        from files.opt.seagate.sspl.setup.sspl_test import SSPLTestCmd
        sspl_test = SSPLTestCmd(self.args)
        sspl_test.validate()
        sspl_test.process()


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
        sspl_bundle_generate = "%s/%s %s" % (self._script_dir, self.script, args)
        output, error, returncode = SimpleProcess(sspl_bundle_generate).run(realtime_output=True)
        if returncode != 0:
            raise SetupError(returncode,
                             "%s - validation failure. %s",
                             self.name,
                             error)


class ManifestSupportBundleCmd(Cmd):
    """Collects enclosure, cluster and node information.
    """

    name = "manifest_support_bundle"
    script = "manifest_support_bundle"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        args = ' '.join(self._args.args)
        manifest_support_bundle = "%s/%s %s" % (self._script_dir, self.script, args)
        output, error, returncode = SimpleProcess(manifest_support_bundle).run(realtime_output=True)
        if returncode != 0:
            raise SetupError(returncode,
                             "%s - validation failure. %s",
                             self.name,
                             error)


class ResetCmd(Cmd):
    """Performs SSPL config reset. Options: hard, soft.
    'hard' is used to reset configs and clean log directory where
    'soft' is to clean only the data path.
    """

    name = "reset"
    script = "sspl_reset"
    process_class=None

    def __init__(self, args):
        super().__init__(args)

    @staticmethod
    def add_args(parser: str, cls: str, name: str):
        """Add Command args for parsing."""
        parsers = parser.add_parser(cls.name, help='%s' % cls.__doc__)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.add_argument('--config', nargs='*', default=[], help='Global config url')
        parsers.add_argument('--type', nargs='*', default=[], help='Reset type (hard|soft)')
        parsers.set_defaults(command=cls)

    def validate(self):
        if not self.args.config:
            raise SetupError(
                errno.EINVAL,
                "%s - Argument validation failure. Global config is required.",
                self.name)

        if not self.args.type:
            raise SetupError(
                errno.EINVAL,
                "%s - Argument validation failure. Reset type is required.",
                self.name)

        reset_type = self.args.type[0]
        if reset_type == "hard":
            self.process_class = "HardReset"
        elif reset_type == "soft":
            self.process_class = "SoftReset"
        else:
            raise SetupError(1, "Invalid reset type specified. Please check usage.")

    def process(self):
        if self.process_class == "HardReset":
            from files.opt.seagate.sspl.setup.sspl_reset import HardReset
            HardReset().process()
        elif self.process_class == "SoftReset":
            from files.opt.seagate.sspl.setup.sspl_reset import SoftReset
            SoftReset().process()

class CheckCmd(Cmd):
    """Validates configs and environment prepared for SSPL initialization.
    """

    name = "check"

    def __init__(self, args):
        super().__init__(args)

        self.SSPL_CONFIGURED="/var/cortx/sspl/sspl-configured"
        self.services = ["rabbitmq-server"]

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        if not os.path.exists(self.SSPL_CONFIGURED):
            error = "SSPL is not configured. Run provisioner scripts in %s" % (self._script_dir)
            syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL3)
            syslog.syslog(syslog.LOG_ERR, error)
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

    def process(self):
        pass


def main(argv: dict):
    try:
        desc = "SSPL Setup Interface"
        command = Cmd.get_command(desc, argv[1:])
        if not command:
            Cmd.usage(argv[0])
            return errno.EINVAL
        command.validate()
        command.process()

    except Exception as e:
        sys.stderr.write("error: %s\n\n" % str(e))
        sys.stderr.write("%s\n" % traceback.format_exc())
        Cmd.usage(argv[0])
        return errno.EINVAL

if __name__ == '__main__':
    sys.exit(main(sys.argv))