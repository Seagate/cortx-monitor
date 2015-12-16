"""
 ****************************************************************************
 Filename:          IEM_Logger.py
 Description:       Handles logging IEM messages to the journal
 Creation Date:     02/26/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import syslog

from zope.interface import implements
from loggers.ILogger import ILogger
from framework.base.debug import Debug
from framework.utils.autoemail import AutoEmail

from systemd import journal
from syslog import (LOG_EMERG, LOG_ALERT, LOG_CRIT, LOG_ERR,
                    LOG_WARNING, LOG_NOTICE, LOG_INFO, LOG_DEBUG)

LOGLEVEL_NAME_TO_LEVEL_DICT = {
    "LOG_EMERG"   : LOG_EMERG,
    "LOG_ALERT"   : LOG_ALERT,
    "LOG_CRIT"    : LOG_CRIT,
    "LOG_ERR"     : LOG_ERR,
    "LOG_WARNING" : LOG_WARNING,
    "LOG_NOTICE"  : LOG_NOTICE,
    "LOG_INFO"    : LOG_INFO,
    "LOG_DEBUG"   : LOG_DEBUG
}

class IEMlogger(Debug):
    """Handles logging IEM messages to the journal"""

    implements(ILogger)

    LOGGER_NAME = "IEMlogger"

    @staticmethod
    def name():
        """ @return: name of the logger."""
        return IEMlogger.LOGGER_NAME

    def __init__(self, conf_reader):
        super(IEMlogger, self).__init__()

        self._autoemailer = AutoEmail(conf_reader)

    def log_msg(self, jsonMsg):
        """logs the IEM message to the journal"""

        self._check_debug(jsonMsg)

        # Get the optional log_level if it exists in msg
        if jsonMsg.get("actuator_request_type").get("logging").get("log_level") is not None:
            log_level = jsonMsg.get("actuator_request_type").get("logging").get("log_level")
        else:
            log_level = "LOG_INFO"

        # Get the message to log in format "IEC: EVENT_CODE: EVENT_STRING: JSON DATA"
        log_msg = jsonMsg.get("actuator_request_type").get("logging").get("log_msg")

        # Encode and remove whitespace,\n,\t if present
        log_msg = json.dumps(log_msg, ensure_ascii=True).encode('utf8')
        log_msg = json.loads(' '.join(log_msg.split()))

        # Try encoding message to handle escape chars if present
        try:
            log_msg = log_msg.encode('utf8')
        except Exception as de:
            self._log_debug("log_msg, no encoding applied, writing to journal: %r" % de)

        result = ""
        try:
            # IEM logging format "IEC: EVENT_CODE: EVENT_STRING: JSON DATA"
            event_code_start = log_msg.index("IEC:") + 4
            event_code_stop  = log_msg.index(":", event_code_start)

            # Parse out the event code and remove any white spaces
            event_code = log_msg[event_code_start : event_code_stop].strip()
            self._log_debug("log_msg, event_code: %s" % event_code)

            msg = log_msg[event_code_stop+1 : ]
            self._log_debug("log_msg, msg: %s" % msg)

            # Use the optional log_level in json message and set it to PRIORITY
            if log_level in LOGLEVEL_NAME_TO_LEVEL_DICT:
                priority = LOGLEVEL_NAME_TO_LEVEL_DICT[log_level]
            self._log_debug("log_msg, priority: %s" % priority)

            # Send it to the journal with the appropriate arguments
            journal.send(msg, MESSAGE_ID=event_code, PRIORITY=priority,
                         SYSLOG_IDENTIFIER="sspl-ll")

            # Send email if priority exceeds LOGEMAILER priority in /etc/sspl-ll.conf
            email_result = self._autoemailer._send_email(log_msg, priority)
            result = "Successfully logged IEM msg, {}".format(email_result)
            self._log_debug("Autoemailer result: %s" % result)

        except Exception as de:
            self._log_debug("log_msg, Error parsing IEM message: %s" % de)
            result = str(de)

        return result
            