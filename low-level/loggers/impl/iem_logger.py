"""
 ****************************************************************************
 Filename:          IEM_Logger.py
 Description:       Handles logging IEM messages to syslog
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
from base.debug import Debug


class IEMlogger(Debug):
    """Handles logging IEM messages to syslog"""

    implements(ILogger)

    def __init__(self, jsonMsg):
        super(IEMlogger, self).__init__()
        self.log_msg(jsonMsg)

    def log_msg(self, jsonMsg):
        """logs the IEM message to syslog"""

        logMsg = jsonMsg.get("actuator_msg_type").get("logging").get("log_msg")

        # Encode and remove whitespace,\n,\t if present
        logMsg = json.dumps(logMsg, ensure_ascii=True).encode('utf8')
        logMsg = json.loads(' '.join(logMsg.split()))

        # Try encoding message to handle escape chars if present
        try:
            logMsg = logMsg.encode('utf8')
        except Exception as de:
            self._log_debug("\n\n_processMsg, no encoding applied, \
                            writing to syslog: %r" % de)            

        # Write message to syslog
        syslog.syslog(logMsg)