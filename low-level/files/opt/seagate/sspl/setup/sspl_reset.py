import os
import shutil

from framework.base.sspl_constants import (PRODUCT_FAMILY,
                                           DATA_PATH,
                                           SSPL_CONFIG_INDEX,
                                           sspl_config_path)
from cortx.utils.service import DbusServiceHandler
from cortx.utils.conf_store import Conf
from files.opt.seagate.sspl.setup.setup_logger import logger


class HardReset:
    """Performs SSPL Hard reset.
    This Interface is used to reset configs and clean log files """

    name = "hard"
    user_present = False

    def del_file(self, filename):
        if os.path.exists(filename):
            os.remove(filename)

    @classmethod
    def del_files_from_dir(cls, fformat, dir_path):
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(fformat):
                    os.remove(os.path.join(root, file))

    def process(self):
        dbus_service = DbusServiceHandler()
        # Stop SSPL service if state is active
        service_state = dbus_service.get_state('sspl-ll.service')
        if service_state._state == 'active':
            logger.info(f'For {self.name}, SSPL service should be stopped'
                        'through HA interfaces')
            logger.info("Stopping SSPL service now...")
            dbus_service.stop('sspl-ll.service')

        # Remove sspl data
        shutil.rmtree(DATA_PATH, ignore_errors=True)

        # Remove log files
        HardReset.del_files_from_dir('.log', f"/var/log/{PRODUCT_FAMILY}/sspl/")
        HardReset.del_files_from_dir('.log.gz',
                                     f"/var/log/{PRODUCT_FAMILY}/sspl/")
        HardReset.del_files_from_dir('.log', f"/var/log/{PRODUCT_FAMILY}/iem/")
        HardReset.del_files_from_dir('.log.gz',
                                     f"/var/log/{PRODUCT_FAMILY}/iem/")

        # Remove .json files and truncate iem log file
        HardReset.del_files_from_dir('.json', "/var/cortx/sspl/data/")
        Conf.load(SSPL_CONFIG_INDEX, sspl_config_path)
        IEM_FILE_PATH = Conf.get(SSPL_CONFIG_INDEX, "IEMSENSOR>log_file_path")
        if os.path.exists(IEM_FILE_PATH):
            with open(IEM_FILE_PATH, 'r+') as f:
                f.truncate()
