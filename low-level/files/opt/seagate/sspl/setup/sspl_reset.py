import os
import shutil

from framework.base.sspl_constants import (PRODUCT_FAMILY,
                                           DATA_PATH,
                                           SSPL_CONFIG_INDEX,
                                           sspl_config_path)
from cortx.utils.service import DbusServiceHandler
from cortx.utils.conf_store import Conf
from files.opt.seagate.sspl.setup.setup_logger import logger


class Reset:
    """Performs SSPL Hard reset.
    Reset Interface is used to reset Data/MetaData
    and clean log files """

    name = "reset"

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
            logger.warning ("SSPL service should have been stopped,"
                            f"before {self.name} interface is invoked")
            logger.warning("Stopping SSPL service now...")
            dbus_service.stop('sspl-ll.service')

        # Remove sspl data
        shutil.rmtree(DATA_PATH, ignore_errors=True)

        # Remove log files
        Reset.del_files_from_dir('.log', f"/var/log/{PRODUCT_FAMILY}/sspl/")
        Reset.del_files_from_dir('.log.gz',
                                 f"/var/log/{PRODUCT_FAMILY}/sspl/")
        Reset.del_files_from_dir('.log', f"/var/log/{PRODUCT_FAMILY}/iem/")
        Reset.del_files_from_dir('.log.gz',
                                 f"/var/log/{PRODUCT_FAMILY}/iem/")

