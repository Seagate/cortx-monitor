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
<<<<<<< HEAD
<<<<<<< HEAD
import time

# using cortx package
from cortx.utils.process import SimpleProcess
from cortx.utils.conf_store import Conf
from cortx.utils.service import Service
from cortx.utils.validator.v_service import ServiceV
from cortx.utils.validator.error import VError
from cortx.sspl.bin.error import SetupError
=======
import subprocess

<<<<<<< HEAD
from cortx.utils.process import SimpleProcess
>>>>>>> EOS-16524: sspl_conf.sh to python (import paths changed and simpleProcess implemented)
=======
from cortx.sspl.lowlevel.framework.utils.utility import Utility
>>>>>>> EOS-16524: sspl_conf.sh to python (changed path to utility.py)
=======
from cortx.utils.process import SimpleProcess
<<<<<<< HEAD
>>>>>>> EOS-16524: sspl_conf.sh to python (minor change)
=======
from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.error import SetupError
>>>>>>> EOS-16524: sspl_conf.sh to python (removed utils.py changes, added error.py)

class Cmd:
    """Setup Command."""

    def __init__(self, args: dict):
        self._args = args.args
        self._script_dir = os.path.dirname(os.path.abspath(__file__))

    @property
    def args(self) -> str:
        return self._args

    @staticmethod
    def usage(prog: str):
<<<<<<< HEAD
        """Print usage instructions."""
        sys.stderr.write(f"""{prog}
            [ -h|--help ]
            [ post_install --config [<global_config_url>] ]
            [ init --config [<global_config_url>] ]
            [ config --config [<global_config_url>] ]
            [ test [sanity|alerts] ]
            [ reset [hard|soft] ]
            [ join_cluster --nodes [<nodes>] ]
            [ manifest_support_bundle [<id>] [<path>] ]
            [ support_bundle [<id>] [<path>] ]
            [ check ]
            \n""")
=======
        """ Print usage instructions."""
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
>>>>>>> EOS-16524: sspl_conf.sh to python (removed utils.py changes, added error.py)

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

<<<<<<< HEAD
<<<<<<< HEAD
=======
    @staticmethod
    def _send_command(command , fail_on_error=True):
        # Note: This function uses subprocess to execute commands, scripts which are not possible to execute
        # through any python routines available. So its usage MUST be limited and used only when no other
        # alternative found.
        output, error, returncode = SimpleProcess(command).run()
        if returncode != 0:
            print("command '%s' failed with error\n%s" % (command, error))
            if fail_on_error:
                sys.exit(1)
            else:
                return str(error)
        if type(output) == bytes:
            output = bytes.decode(output)
        return str(output)

    @staticmethod
    def _call_script(script_dir: str, args: list):
        script_args_lst = [script_dir]+args
        subprocess.call(script_args_lst, shell=False)

=======
>>>>>>> EOS-16524: sspl_conf.sh to python (changed path to utility.py)

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
        setup_sspl = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(setup_sspl).run()
        if returncode != 0:
            raise SetupError(returncode, error)

>>>>>>> EOS-16524: sspl_conf.sh to python (import of conf_vased_sensors_enable and few changes)

class JoinClusterCmd(Cmd):
    """Join nodes in cluster. To join mutiple nodes, use delimeter ","
    between node names. ie.node1,node2
    """

    name = "join_cluster"
    script = "setup_rabbitmq_cluster"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        if not self.args:
            raise SetupError(1,
                             "Validation failure. %s",
                             "join_cluster requires comma separated node names as argument.")
        if (len(self.args) != 2) or (self.args[0] != "--nodes"):
            raise SetupError(1,
                             "%s - Argument validation failure. %s",
                             self.name,
                             "Check usage.")

    def process(self):
<<<<<<< HEAD
<<<<<<< HEAD
<<<<<<< HEAD
        from cortx.sspl.bin.setup_rabbitmq_cluster import RMQClusterConfiguration
        RMQClusterConfiguration(self.args[1]).process()
=======
        Cmd._call_script(f"{self._script_dir}/{self.script}", self._args)
=======
        Utility.call_script(f"{self._script_dir}/{self.script}", self._args)
<<<<<<< HEAD
>>>>>>> EOS-16524: sspl_conf.sh to python (changed path to utility.py)
        from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.sspl_config import Config
        Config(self.args).process()
>>>>>>> EOS-16524: sspl_conf.sh to python (changed imports in sspl_setup)
=======
        try :
            from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.sspl_config import SSPLConfig
            SSPLConfig(self.args).process()
        except Exception as error:
            print(error)
            sys.exit(1)
>>>>>>> EOS-16524: sspl_config.sh to python (removed usage(), added Expection handling)
=======
        setup_rabbitmq_cluster = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(setup_rabbitmq_cluster).run()
        if returncode != 0:
            raise SetupError(returncode, error)

        # TODO: Replace the below code once sspl_config script implementation is done.
        sspl_config = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(sspl_config).run()
        if returncode != 0:
<<<<<<< HEAD
            sys.stderr.write("error: %s\n\n" % str(error))
            sys.exit(errno.EINVAL)
>>>>>>> EOS-16524: sspl_conf.sh to python (minor change)
=======
            raise SetupError(returncode, error)
>>>>>>> EOS-16524: sspl_conf.sh to python (removed utils.py changes, added error.py)


class PostInstallCmd(Cmd):
    """Prepare the environment for sspl service."""

    name = "post_install"

    def __init__(self, args: dict):
        super().__init__(args)

    def validate(self):
        if not self.args:
            raise SetupError(1,
                             "%s - Argument validation failure. %s",
                             self.name,
                             "Post install requires global config.")
        if (len(self.args) != 2) or (self.args[0] != "--config"):
            raise SetupError(1,
                             "%s - Argument validation failure. %s",
                             self.name,
                             "Check usage.")
        global_config = self.args[1]
        Conf.load('global_config', global_config)
        product = Conf.get('global_config', 'release>product')
        if not product:
            raise SetupError(1,
                             "%s - validation failure. %s",
                             self.name,
                             "Product not found in %s" % (global_config))

    def process(self):
        from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.sspl_post_install import SSPLPostInstall
        SSPLPostInstall(self.args[1]).process()


class InitCmd(Cmd):
    """Creates data path and checks required role."""

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
    """Configues SSPL role, logs and sensors needs to be enabled."""

    name = "config"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
        from cortx.sspl.lowlevel.files.opt.seagate.sspl.setup.sspl_config import SSPLConfig
        try:
            SSPLConfig(self.args).process()
        except Exception:
            raise


class TestCmd(Cmd):
    """Starts test based on plan (sanity | alerts)."""

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
    """Collects SSPL support bundle."""

    name = "support_bundle"
    script = "sspl_bundle_generate"

    def __init__(self, args):
        super().__init__(args)

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        pass

    def process(self):
<<<<<<< HEAD
<<<<<<< HEAD
        args = ' '.join(self._args)
        sspl_bundle_generate = "%s/%s %s" % (self._script_dir, self.script, args)
        output, error, returncode = SimpleProcess(sspl_bundle_generate).run()
        if returncode != 0:
            raise SetupError(returncode, "%s - validation failure. %s", self.name, error)
=======
        Utility.call_script(f"{self._script_dir}/{self.script}", self._args)
>>>>>>> EOS-16524: sspl_conf.sh to python (changed path to utility.py)
=======
        sspl_bundle_generate = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(sspl_bundle_generate).run()
        if returncode != 0:
<<<<<<< HEAD
            sys.stderr.write("error: %s\n\n" % str(error))
            sys.exit(errno.EINVAL)
>>>>>>> EOS-16524: sspl_conf.sh to python (minor change)
=======
            raise SetupError(returncode, error)
>>>>>>> EOS-16524: sspl_conf.sh to python (removed utils.py changes, added error.py)


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
<<<<<<< HEAD
<<<<<<< HEAD
        args = ' '.join(self._args)
        manifest_support_bundle = "%s/%s %s" % (self._script_dir, self.script, args)
        output, error, returncode = SimpleProcess(manifest_support_bundle).run()
        if returncode != 0:
            raise SetupError(returncode, "%s - validation failure. %s", self.name, error)
=======
        Utility.call_script(f"{self._script_dir}/{self.script}", self._args)
>>>>>>> EOS-16524: sspl_conf.sh to python (changed path to utility.py)
=======
        manifest_support_bundle = f"{self._script_dir}/{self.script} {' '.join(self._args)}"
        output, error, returncode = SimpleProcess(manifest_support_bundle).run()
        if returncode != 0:
<<<<<<< HEAD
            sys.stderr.write("error: %s\n\n" % str(error))
            sys.exit(errno.EINVAL)
>>>>>>> EOS-16524: sspl_conf.sh to python (minor change)
=======
            raise SetupError(returncode, error)
>>>>>>> EOS-16524: sspl_conf.sh to python (removed utils.py changes, added error.py)


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

<<<<<<< HEAD
<<<<<<< HEAD
        from cortx.sspl.bin.sspl_constants import PRODUCT_FAMILY
=======
        from cortx.sspl.lowlevel.framework.base.sspl_constants import PRODUCT_FAMILY
>>>>>>> EOS-16524: sspl_conf.sh to python (import paths changed and simpleProcess implemented)
=======
        from cortx.sspl.bin.sspl_constants import PRODUCT_FAMILY
>>>>>>> EOS-16524: sspl_conf.sh to python (minor change)

        self.SSPL_CONFIGURED="/var/%s/sspl/sspl-configured" % (PRODUCT_FAMILY)
        self.services = ["rabbitmq-server", "sspl-ll"]
        Service('dbus').process('start', 'sspl-ll.service')

    def validate(self):
        # Common validator classes to check Cortx/system wide validator
        if not os.path.exists(self.SSPL_CONFIGURED):
            error = "SSPL is not configured. Run provisioner scripts in %s" % (self._script_dir)
            syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL3)
            syslog.syslog(syslog.LOG_ERR, error)
            raise SetupError(1, "%s - validation failure. %s", self.name, error)
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
<<<<<<< HEAD
        pass

=======
        #self.validate_consul_config.validate_config()
        if os.path.exists(self.SSPL_CONFIGURED):
            return
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_LOCAL3)
        syslog.syslog(syslog.LOG_ERR, f"SSPL is not configured. Run provisioner scripts in {self._script_dir}.")
        raise SetupError(errno.EINVAL,
                "SSPL is not configured. Run provisioner scripts in %s.",
                self._script_dir)
>>>>>>> EOS-16524: sspl_conf.sh to python (removed utils.py changes, added error.py)

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
