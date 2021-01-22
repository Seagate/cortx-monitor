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

# using cortx package
from cortx.sspl.bin.error import SetupError
from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store import Conf

class Cmd:
    """Setup Command.

    """

    def __init__(self, args: dict):
        self._args = args.args
        self._script_dir = os.path.dirname(os.path.abspath(__file__))

    @property
    def args(self) -> str:
        return self._args

    @staticmethod
    def usage(prog: str):
        """Print usage instructions."""
        sys.stderr.write(f"""{prog}
            [ -h|--help ]
            [ post_install [<global_config_url>] ]
            [ init [<global_config_url>] ]
            [ config [<global_config_url>] ]
            [ test [sanity|alerts] ]
            [ reset [hard|soft] ]
            [ join_cluster [<nodes>] ]
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

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        setup_rabbitmq_cluster = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(setup_rabbitmq_cluster).run()
        if returncode != 0:
            raise SetupError(returncode, "%s - validation failure. %s", self.name, error)

        # TODO: Replace the below code once sspl_config script implementation is done.
        sspl_config = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(sspl_config).run()
        if returncode != 0:
            raise SetupError(returncode, "%s - validation failure. %s", self.name, error)


class PostInstallCmd(Cmd):
    """Prepare the environment for sspl service.
    """

    name = "post_install"

    def __init__(self, args: dict):
        super().__init__(args)

    def validate(self):
        if not self.args:
            raise SetupError(1,
                             "%s - validation failure. %s",
                             self.name,
                             "Post install requires global config.")
        global_config = self.args[0]
        Conf.load('global_config', global_config)
        product = Conf.get('global_config', 'cluster>product')
        if not product:
            raise SetupError(1,
                             "%s - validation failure. %s",
                             self.name,
                             "Product not found in %s" % (global_config))

    def process(self):
        from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.sspl_post_install import SSPLPostInstall
        SSPLPostInstall(self.args).process()


class InitCmd(Cmd):
    """Creates data path and checks required role.
    """

    name = "init"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        # TODO: Import relevant python script here for further execution.
        pass


class ConfigCmd(Cmd):
    """Configues SSPL role, logs and sensors needs to be enabled.
    """

    name = "config"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        # TODO: Import relevant python script here for further execution.
        pass


class TestCmd(Cmd):
    """Starts test based on plan (sanity | alerts).
    """

    name = "test"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        # TODO: Import relevant python script here for further execution.
        pass


class SupportBundleCmd(Cmd):
    """Collects SSPL support bundle.
    """

    name = "support_bundle"
    script = "sspl_bundle_generate"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        sspl_bundle_generate = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(sspl_bundle_generate).run()
        if returncode != 0:
            raise SetupError(returncode, "%s - validation failure. %s", self.name, error)


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
        manifest_support_bundle = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(manifest_support_bundle).run()
        if returncode != 0:
            raise SetupError(returncode, "%s - validation failure. %s", self.name, error)


class ResetCmd(Cmd):
    """Performs SSPL config reset. Options: hard, soft.
    'hard' is used to reset configs and clean log directory where
    'soft' is to clean only the data path.
    """

    name = "reset"
    script = "sspl_reset"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        # TODO: Import relevant python script here for further execution.
        pass


class CheckCmd(Cmd):
    """Validates configs and environment prepared for SSPL initialization.
    """

    name = "check"

    def __init__(self, args):
        super().__init__(args)

        from cortx.sspl.bin.sspl_constants import PRODUCT_FAMILY

        self.SSPL_CONFIGURED=f"/var/{PRODUCT_FAMILY}/sspl/sspl-configured"

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        if not os.path.exists(self.SSPL_CONFIGURED):
            error = f"SSPL is not configured. Run provisioner scripts in {self._script_dir}"
            syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL3)
            syslog.syslog(syslog.LOG_ERR, error)
            raise SetupError(1, "%s - validation failure. %s", self.name, error)

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
