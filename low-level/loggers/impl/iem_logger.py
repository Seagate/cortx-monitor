# Copyright (c) 2001-2015 Seagate Technology LLC and/or its Affiliates
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
  Description:       Handles logging IEM messages to the journal
 ****************************************************************************
"""

import json
import syslog

from zope.interface import implementer
from loggers.ILogger import ILogger
from framework.base.debug import Debug
from framework.utils.autoemail import AutoEmail
from framework.utils.service_logging import logger

try:
   from systemd import journal
   use_journal=True
except ImportError:
    use_journal=False

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

@implementer(ILogger)
class IEMlogger(Debug):
    """Handles logging IEM messages to the journal"""

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

        # Encode and remove blankspace,\n,\t if present
        log_msg = json.dumps(log_msg, ensure_ascii=True).encode('utf8')
        log_msg = json.loads(b' '.join(log_msg.split()))

        # Try encoding message to handle escape chars if present
        try:
            log_msg = log_msg.encode('utf8')
        except Exception as de:
            self._log_debug("log_msg, no encoding applied, writing to journal: %r" % de)

        result = ""
        try:
            # IEM logging format "IEC: EVENT_CODE: EVENT_STRING: {JSON DATA}"
            event_code_start = log_msg.index("IEC:") + 4
            event_code_stop  = log_msg.index(":", event_code_start)

            # Parse out the event code and remove any blank spaces
            event_code = log_msg[event_code_start : event_code_stop].strip()
            self._log_debug("log_msg: %s" % log_msg)
            self._log_debug("IEC: %s" % event_code)

            # Use the optional log_level in json message and set it to PRIORITY
            if log_level in LOGLEVEL_NAME_TO_LEVEL_DICT:
                priority = LOGLEVEL_NAME_TO_LEVEL_DICT[log_level]
            else:
                priority = LOG_INFO

            # Send it to the journal with the appropriate arguments
            if use_journal:
                journal.send(log_msg, MESSAGE_ID=event_code, PRIORITY=priority,
                         SYSLOG_IDENTIFIER="sspl-ll")
            else:
                logger.info(log_msg)

            # Send email if priority exceeds LOGEMAILER priority in /etc/sspl-ll.conf
            result = self._autoemailer._send_email(log_msg, priority)
            self._log_debug("Emailing result: {}".format(result))

        except Exception as de:
            # Dump to journal anyway as it could be useful for debugging format errors
            #result = "IEMlogger, log_msg, Error parsing IEM: {}".format(str(de))
            #journal.send(result, PRIORITY=LOG_WARNING, SYSLOG_IDENTIFIER="sspl-ll")
            journal.send(log_msg.decode("utf-8"), PRIORITY=LOG_WARNING, SYSLOG_IDENTIFIER="sspl-ll")

        return result
