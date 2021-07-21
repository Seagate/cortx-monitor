# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

# ****************************************************************************
#  Description:       Logger for sspl mini provisioner interface scripts
# ****************************************************************************

import logging
from framework.utils.utility import Utility
from framework.base.sspl_constants import SETUP_LOG_PATH
import sys

logger_facility = "sspl-setup"
_logger = logging.getLogger(logger_facility)

def init_logging(syslog_host="localhost", syslog_port=514, console_output=False):
    """Initialize logging for sspl-setup."""
    _logger.setLevel(logging.INFO)
    # set Logging Handlers
    Utility().create_file(SETUP_LOG_PATH)

    handler = logging.handlers.RotatingFileHandler(
        SETUP_LOG_PATH,
        mode='a',
        maxBytes=2000000,
        backupCount=5)

    fformat = "%(asctime)s %(name)s[%(process)d]: " \
                "%(levelname)s %(message)s (%(filename)s:%(lineno)d)"
    formatter = logging.Formatter(fformat, datefmt='%b %d %H:%M:%S')
    handler.setFormatter(formatter)
    _logger.addHandler(handler)
    if console_output:
        console = logging.StreamHandler(sys.stderr)
        console.setFormatter(formatter)
        _logger.addHandler(console)

logger = _logger
