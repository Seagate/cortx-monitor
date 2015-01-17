"""
 ****************************************************************************
 Filename:          service_logging.py
 Description:       logging utilities for the daemon services

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.

 ****************************************************************************
 All relevant license information (GPL, FreeBSD, etc)
 ****************************************************************************
"""

import logging.handlers
import time

logger_facility = "sspl-ll"
logger = logging.getLogger(logger_facility)

MAX_SYSLOG_CONNECT_ATTEMPTS = 120
RECONNECT_DELAY_INTERVAL_SECONDS = 1

LOG_CRITICAL = "CRITICAL"
LOG_ERROR    = "ERROR"
LOG_WARN     = "WARN"
LOG_WARNING  = "WARNING"
LOG_INFO     = "INFO"
LOG_DEBUG    = "DEBUG"
LOG_NOTSET   = "NOTSET"

# Dictionary to convert loglevel strings to loglevels
LOGLEVEL_NAME_TO_LEVEL_DICT = {
    LOG_CRITICAL: logging.CRITICAL,
    LOG_ERROR: logging.ERROR,
    LOG_WARN: logging.WARNING,
    LOG_WARNING: logging.WARNING,
    LOG_INFO: logging.INFO,
    LOG_DEBUG: logging.DEBUG,
    LOG_NOTSET: logging.NOTSET,
}


def init_logging(dcs_service_name, log_level=LOG_INFO):
    """Initialize logging to log to syslog"""
    warning_message = None
    if log_level not in LOGLEVEL_NAME_TO_LEVEL_DICT.keys():
        warning_message = str(
            "Invalid log_level '{0}' specified. Using "
            "default log_level '{1}' instead.".format(log_level, LOG_INFO))
        log_level = LOG_INFO
    logger.setLevel(LOGLEVEL_NAME_TO_LEVEL_DICT[log_level])
    num_attempts = 1
    handler = logging.NullHandler()
    while True:
        try:
            handler = logging.handlers.SysLogHandler(address='/dev/log')
            syslog_format = "%(name)s[%(process)d]: " \
                "%(levelname)s %(message)s (%(filename)s:%(lineno)d)"
            formatter = logging.Formatter(syslog_format)
            handler.setFormatter(formatter)
            break
        except:
            if num_attempts <= MAX_SYSLOG_CONNECT_ATTEMPTS:
                num_attempts += 1
                time.sleep(RECONNECT_DELAY_INTERVAL_SECONDS)
                continue
            else:
                print "Warning: Unable to connect to syslog for logging"
                break

    logger.addHandler(handler)
    logger.info(
        "Logging has been initialized for sspl '%s' service after %d attempts",
        dcs_service_name, num_attempts)
    if warning_message is not None:
        logger.warning(warning_message)
