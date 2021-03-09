import os
import shutil

from framework.base.sspl_constants import (PRODUCT_FAMILY,
                                           file_store_config_path,
                                           SSPL_CONFIGURED,
                                           DATA_PATH,
                                           SSPL_CONFIG_INDEX,
                                           sspl_config_path)
from cortx.utils.process import SimpleProcess
from cortx.utils.service import Service
from cortx.utils.conf_store import Conf
from .setup_error import SetupError


class HardReset:
    """Performs SSPL Hard reset.
    'hard' is used to reset configs and clean log directory """

    name = "hard"
    user_present=False

    def del_file(self, filename):
        if os.path.exists(filename):
            os.remove(filename)

    def process(self):
        # stop sspl service
        Service('dbus').stop('sspl-ll.service')

        # Remove sspl_conf
        self.del_file(file_store_config_path)

        # Remove sspl-configured file
        self.del_file(SSPL_CONFIGURED)

        # Remove sspl data
        shutil.rmtree(DATA_PATH, ignore_errors=True)

        # Remove sspl-ll user if preset
        CMD = "id -u sspl-ll"
        output, error, returncode = SimpleProcess(CMD).run()
        if returncode != 0:
            raise SetupError(returncode, "ERROR: %s - CMD %s", error, CMD)
        else:
            self.user_present=True

        if self.user_present:
            CMD="/usr/sbin/userdel sspl-ll"
            output, error, returncode = SimpleProcess(CMD).run()
            if returncode != 0:
                raise SetupError(returncode, "ERROR: %s - CMD %s", error, CMD)

        # Remove log directories
        shutil.rmtree(f"/var/log/{PRODUCT_FAMILY}/sspl", ignore_errors=True)
        shutil.rmtree(f"/var/log/{PRODUCT_FAMILY}/iem", ignore_errors=True)

        # Remove rsyslog config files
        self.del_file("/etc/rsyslog.d/0-iemfwd.conf")
        self.del_file("/etc/rsyslog.d/1-ssplfwd.conf")

        # Remove logrotate config files
        self.del_file("/etc/logrotate.d/iem_messages")
        self.del_file("/etc/logrotate.d/sspl_logs")

        # Remove SSPL configuration files
        shutil.rmtree("/etc/sspl-ll", ignore_errors=True)
        self.del_file("/etc/sspl.conf.bak")

class SoftReset:
    """Performs SSPL Soft reset.
    'soft' is to clean only the data path."""

    name = "soft"

    def process(self):
        # Remove .json files and truncate iem log file
        Conf.load(SSPL_CONFIG_INDEX, sspl_config_path)
        for root, dirs, files in os.walk("/var/cortx/sspl/data/"):
            for file in files:
                if file.endswith(".json"):
                    os.remove(os.path.join(root, file))
        IEM_FILE_PATH = Conf.get(SSPL_CONFIG_INDEX, "IEMSENSOR>log_file_path")
        if os.path.exists(IEM_FILE_PATH):
            with open(IEM_FILE_PATH, 'r+') as f:
                f.truncate()
