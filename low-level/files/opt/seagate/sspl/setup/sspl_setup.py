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
import subprocess
from cortx.sspl.bin.utility import Utility

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
        sys.stderr.write(
            f"{prog} [setup [-p <LDR_R2>]|post_install [-p <LDR_R2>]|init [-dp] [-r <vm>]|config [-f] [-r <vm>]\n"
            "|test [self|sanity]|reset [hard -p <LDR_R21>|soft]|join_cluster [-n <nodes>]\n"
            "|manifest_support_bundle [<id>] [<path>]|support_bundle [<id>] [<path>]]\n"
            "setup options:\n"
            "\t -p Product name\n"
            "join_cluster options:\n"
            "\t -n Node names\n"
            "init options:\n"
            "\t -dp Create configured datapath\n"
            "\t -r  Role to be configured on the current node\n"
            "config options:\n"
            "\t -f  Force reinitialization. Do not prompt\n"
            "\t -r  Role to be configured on the current node"
            "post_install options:\n"
            "\t -p Product to be configured\n"
            "reset options:\n"
            "\t -p Product to be configured\n")

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
        parsers = parser.add_parser(cls.name, help='setup %s' % name)
        parsers.add_argument('args', nargs='*', default=[], help='args')
        parsers.set_defaults(command=cls)


class SetupCmd(Cmd):
    """SSPL Setup Cmd.
    
    """

    name = "setup"
    script = "setup_sspl"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        Utility._call_script(f"{self._script_dir}/{self.script}", self._args)


class JoinClusterCmd(Cmd):
    """Setup Join Cluster Cmd.
    
    """

    name = "join_cluster"
    script = "setup_rabbitmq_cluster"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        Utility._call_script(f"{self._script_dir}/{self.script}", self._args)
        # TODO: Replace the below code once sspl_config script implementation is done.
        Utility._call_script(f"{self._script_dir}/sspl_config", ['-f'])


class PostInstallCmd(Cmd):
    """PostInstall Setup Cmd.
    
    """

    name = "post_install"

    def __init__(self, args: dict):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.sspl_post_install import SSPLPostInstall
        SSPLPostInstall(self.args).process()


class InitCmd(Cmd):
    """Init Setup Cmd.
    
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
    """Setup Config Cmd.
    
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
    """SSPL Test Cmd.
    
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
    """SSPL Support Bundle Cmd.
    
    """

    name = "support_bundle"
    script = "sspl_bundle_generate"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        Utility._call_script(f"{self._script_dir}/{self.script}", self._args)


class ManifestSupportBundleCmd(Cmd):
    """Manifest Support Bundle Cmd.
    
    """

    name = "manifest_support_bundle"
    script = "manifest_support_bundle"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        Utility._call_script(f"{self._script_dir}/{self.script}", self._args)


class ResetCmd(Cmd):
    """Setup Reset Cmd.
    
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
    """SSPL Check Cmd.
    
    """

    name = "check"

    def __init__(self, args):
        super().__init__(args)

        from cortx.sspl.bin.sspl_constants import PRODUCT_FAMILY

        self.SSPL_CONFIGURED=f"/var/{PRODUCT_FAMILY}/sspl/sspl-configured"

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        # Onward LDR_R2, consul will be abstracted out and won't exist as hard dependency for SSPL
        #from files.opt.seagate.sspl.setup import validate_consul_config
        #self.validate_consul_config = validate_consul_config
        pass

    def process(self):
        #self.validate_consul_config.validate_config()
        if os.path.exists(self.SSPL_CONFIGURED):
            sys.exit(0)
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL3)
        syslog.syslog(syslog.LOG_ERR, f"SSPL is not configured. Run provisioner scripts in {self._script_dir}.")
        sys.exit(1)

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
