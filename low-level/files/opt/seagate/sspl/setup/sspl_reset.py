import os
import shutil

from framework.base.sspl_constants import (PRODUCT_FAMILY,
                                           DATA_PATH,
                                           SSPL_CONFIG_INDEX,
                                           sspl_config_path)
from cortx.utils.service import DbusServiceHandler
from cortx.utils.conf_store import Conf
from cortx.utils.process import SimpleProcess
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
    def reset_log_files(cls, fformat, dir_path, del_file=False):
        for root, _, files in os.walk(dir_path):
            for file in files:
                if file.endswith(fformat):
                    if del_file:
                        os.remove(os.path.join(root, file))
                        return
                    cmd= f"truncate -s 0 > {os.path.join(root, file)}"
                    _, error, returncode = SimpleProcess(cmd).run()
                    if returncode != 0:
                        logger.error("Failed to clear log file data"
                                     f"ERROR:{error} CMD:{cmd}")

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

        # Clear log data from log files and delete 'log.gz' files
        Reset.reset_log_files('.log', f"/var/log/{PRODUCT_FAMILY}/sspl/")
        Reset.reset_log_files('.log', f"/var/log/{PRODUCT_FAMILY}/iem/")
        Reset.reset_log_files('.log.gz',
                              f"/var/log/{PRODUCT_FAMILY}/sspl/",
                              del_file=True)
        Reset.reset_log_files('.log.gz',
                              f"/var/log/{PRODUCT_FAMILY}/iem/",
                              del_file=True)
