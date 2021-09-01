# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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


import logging.handlers
import time


logger_facility = "sspl-ll"
logger = logging.getLogger(logger_facility)

MAX_SYSLOG_CONNECT_ATTEMPTS = 120
RECONNECT_DELAY_INTERVAL_SECONDS = 1

LOG_CRITICAL = "CRITICAL"
LOG_ERROR = "ERROR"
LOG_WARNING = "WARNING"
LOG_INFO = "INFO"
LOG_DEBUG = "DEBUG"
LOG_NOTSET = "NOTSET"

# Dictionary to convert loglevel strings to loglevels
LOGLEVEL_NAME_TO_LEVEL_DICT = {
    LOG_CRITICAL: logging.CRITICAL,
    LOG_ERROR: logging.ERROR,
    LOG_WARNING: logging.WARNING,
    LOG_INFO: logging.INFO,
    LOG_DEBUG: logging.DEBUG,
    LOG_NOTSET: logging.NOTSET,
}


def init_logging(dcs_service_name, log_level=LOG_INFO):
    """Initialize logging to log to syslog"""

    warning_message = None
    if log_level not in list(LOGLEVEL_NAME_TO_LEVEL_DICT.keys()):
        warning_message = str(
            "Invalid log_level '{0}' specified. Using "
            "default log_level '{1}' instead.".format(log_level, LOG_INFO)
        )
        log_level = LOG_INFO
    logger.setLevel(LOGLEVEL_NAME_TO_LEVEL_DICT[log_level])
    num_attempts = 1

    while True:
        try:
            handler = logging.handlers.SysLogHandler(address="/dev/log")
            syslog_format = (
                "%(name)s[%(process)d]: "
                "%(levelname)s %(message)s (%(filename)s:%(lineno)d)"
            )
            formatter = logging.Formatter(syslog_format)
            handler.setFormatter(formatter)
            break
        except Exception:
            if num_attempts <= MAX_SYSLOG_CONNECT_ATTEMPTS:
                num_attempts += 1
                time.sleep(RECONNECT_DELAY_INTERVAL_SECONDS)
                continue
            else:
                print("Warning: Unable to connect to syslog for logging")
                break

    logger.addHandler(handler)
    logger.info(
        "Logging has been initialized for sspl '%s' service after %d attempts to level %s",
        dcs_service_name,
        num_attempts,
        log_level,
    )
    if warning_message is not None:
        logger.warning(warning_message)
