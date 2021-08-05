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
from cortx.utils.process import SimpleProcess
from framework.utils.service_logging import logger


class FileUtils:
    """Handle file operations."""

    @staticmethod
    def delete_or_truncate_files(path, fformat=None, del_file=False, del_dir=False):
        """Clean log files and delete files from dir."""
        if not os.path.exists(path):
            logger.info(f"{path} path doesn't exists.")
            return
        try:
            if fformat:
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(fformat):
                            if del_file:
                                os.remove(os.path.join(root, file))
                                return
                            cmd = f"truncate -s 0 > {os.path.join(root, file)}"
                            _, error, returncode = SimpleProcess(cmd).run()
                            if returncode != 0:
                                logger.error(
                                    "Failed to clear log file data. "
                                    f"ERROR:{error} CMD:{cmd}")
            else:
                if os.path.isfile(path) and del_file:
                    os.remove(path)
                elif os.path.islink(path):
                    os.unlink(path)
                elif os.path.isdir(path) and del_dir:
                    shutil.rmtree(path, ignore_errors=True)
        except OSError as err:
            raise FileUtilsError(
                err.errno, "Failed to remove %s path, ERROR: '%s, %s'" % path,
                err.strerror, err.filename)


class FileUtilsError(Exception):

    def __init__(self, rc, message, *args):
        """Initialize the error information."""
        self._rc = rc
        self._desc = message % (args)

    @property
    def rc(self):
        return self._rc

    @property
    def desc(self):
        return self._desc

    def __str__(self):
        """Return the error string."""
        if self._rc == 0:
            return self._desc
        return "error(%d): %s" % (self._rc, self._desc)
