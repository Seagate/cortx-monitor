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
import os


try:
    from systemd import journal
    use_journal = True
except ImportError:
    use_journal = False


logger_facility = "sspl-ll"
_logger = logging.getLogger(logger_facility)

MAX_SYSLOG_CONNECT_ATTEMPTS = 120
RECONNECT_DELAY_INTERVAL_SECONDS = 1
SYSLOG_IDENTIFIER = "sspl"

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


def init_logging(dcs_service_name, log_level=LOG_INFO, syslog_host="localhost", syslog_port=514):
    """Initialize logging to log to syslog"""

    warning_message = None
    if log_level not in list(LOGLEVEL_NAME_TO_LEVEL_DICT.keys()):
        warning_message = str(
            "Invalid log_level '{0}' specified. Using "
            "default log_level '{1}' instead.".format(log_level, LOG_INFO))
        log_level = LOG_INFO
    _logger.setLevel(LOGLEVEL_NAME_TO_LEVEL_DICT[log_level])
    num_attempts = 1
    handler = None

    while True:
        try:
            handler = logging.handlers.SysLogHandler(
                address=(syslog_host, syslog_port))
            syslog_format = "%(name)s[%(process)d]: " \
                "%(levelname)s %(message)s (%(filename)s:%(lineno)d)"
            formatter = logging.Formatter(syslog_format)
            handler.setFormatter(formatter)
            break
        except Exception as e:
            print('Syslog connect exception: {}. Retrying...'.format(e))
            if num_attempts <= MAX_SYSLOG_CONNECT_ATTEMPTS:
                num_attempts += 1
                time.sleep(RECONNECT_DELAY_INTERVAL_SECONDS)
                continue
            else:
                print("Warning: Unable to connect to syslog for logging")
                break
    _logger.addHandler(handler)
    _logger.info(f"Logging has been initialized for sspl {dcs_service_name} \
                  service after {num_attempts} attempts to level {log_level}")
    if warning_message is not None:
        _logger.warning(warning_message)


class Logger:
    """
    A wrapper class to wrap logging functionality.
    """

    def __init__(self, _logger):
        self._logger = _logger

    def info(self, *args, **kwargs):
        self._logger.info(*args, **kwargs)

    def debug(self, *args, **kwargs):
        self._logger.debug(*args, **kwargs)

    def warn(self, *args, **kwargs):
        self._logger.warn(*args, **kwargs)

    def warning(self, *args, **kwargs):
        self._logger.warn(*args, **kwargs)

    def exception(self, *args, **kwargs):
        self._logger.exception(*args, **kwargs)

    def error(self, *args, **kwargs):
        self._logger.error(*args, **kwargs)

    def critical(self, *args, **kwargs):
        self._logger.critical(*args, **kwargs)

    def setLevel(self, *args, **kwargs):
        self._logger.setLevel(*args, **kwargs)

# This wrapper class was defined with an intention to add other handle
# to logger.
# But, because of this Logger class object, The filenamwe and lineno is
# getting set with current filename and lineno. Because of this, every info,
# warning and debug message which is getting logged are with
# filename service_logging.py and lineno as 103 for info as it is called
# at line no 103 here in this file. WHich is not serving the actual purpose
# of logging. So, switching back to default logging use.
# logger = Logger(_logger)

# Make use of python logger
logger = _logger

# TODO: Instead of python logger, make use of this custom logger class and
# which should also solve problem of line no and file name
