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

"""
 ****************************************************************************
  Description:       logging utilities for the daemon services
 ****************************************************************************
"""

import sys
import os
import syslog
from cortx.utils.log import Log

def init_logging(dcs_service_name, file_path, log_level="INFO"):
    """Initialize logging for SSPL component."""
    try:
        Log.init(service_name=dcs_service_name, log_path=file_path, level=log_level)
    except Exception as err:
        syslog.syslog(f"[ Error ] CORTX Logger Init failed with error {err}")
        sys.exit(os.EX_SOFTWARE)

logger = Log


class CustomLog:
    """A wrapper class to add extra service name
    as prefix to sspl logs."""
    def __init__(self, svc_name):
        self.service = svc_name

    def svc_log(self, msg):
        return f"[{self.service}] {msg}"
