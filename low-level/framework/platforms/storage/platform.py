#!/usr/bin/python3

# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
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
# please email opensource@seagate.com or cortx-questions@seagate.com

import errno
from framework.utils.service_logging import logger
from framework.base import sspl_constants as const


class Platform:
    """Provides information about platform."""

    def __init__(self):
        """Initialize instance."""
        super().__init__()

    @staticmethod
    def validate_storage_type_support(log, Error, storage_type):
        """Check for supported storage type."""
        logger.debug(log.svc_log(f"Storage Type:{storage_type}"))
        if not storage_type:
            msg = "ConfigError: storage type is unknown."
            logger.error(log.svc_log(msg))
            raise Error(errno.EINVAL, msg)
        if storage_type.lower() not in const.RESOURCE_MAP["storage_type_supported"]:
            msg = f"{log.service} provider is not supported for storage type '{storage_type}'"
            logger.error(log.svc_log(msg))
            raise Error(errno.EINVAL, msg)
