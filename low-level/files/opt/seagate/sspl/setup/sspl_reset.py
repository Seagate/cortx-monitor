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

import os
import shutil

from framework.base.sspl_constants import (PRODUCT_FAMILY,
                                           DATA_PATH,
                                           SSPL_CONFIG_INDEX,
                                           sspl_config_path)
from cortx.utils.service import DbusServiceHandler
from cortx.utils.conf_store import Conf
from files.opt.seagate.sspl.setup.setup_logger import logger
from framework.utils.file_utils import FileUtils


class Reset:
    """Performs SSPL Hard reset.
    Reset Interface is used to reset Data/MetaData
    and clean log files """

    name = "reset"

    def del_file(self, filename):
        if os.path.exists(filename):
            os.remove(filename)


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
        FileUtils.reset_log_files(f"/var/log/{PRODUCT_FAMILY}/sspl/", '.log')
        FileUtils.reset_log_files(f"/var/log/{PRODUCT_FAMILY}/iem/", '.log')
        FileUtils.reset_log_files(
            f"/var/log/{PRODUCT_FAMILY}/sspl/", '.log.gz', del_file=True)
        FileUtils.reset_log_files(
            f"/var/log/{PRODUCT_FAMILY}/iem/", '.log.gz', del_file=True)
