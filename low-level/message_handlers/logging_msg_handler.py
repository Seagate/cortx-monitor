"""
 ****************************************************************************
 Filename:          logging_msg_handler.py
 Description:       Message Handler for logging Messages
 Creation Date:     02/25/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import syslog
import pika
import os

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

from loggers.impl.iem_logger import IEMlogger


class LoggingMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for logging Messages"""

    MODULE_NAME = "LoggingMsgHandler"
    PRIORITY    = 2

    # Section and keys in configuration file
    LOGGINGMSGHANDLER = MODULE_NAME.upper()


    @staticmethod
    def name():
        """ @return: name of the module."""
        return LoggingMsgHandler.MODULE_NAME

    def __init__(self):
        super(LoggingMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(LoggingMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(LoggingMsgHandler, self).initializeMsgQ(msgQlist)

    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Starting thread")
        try:
            # Block on message queue until it contains an entry
            jsonMsg = self._readMyMsgQ()
            self._log_debug("run jsonMsg: %s" % jsonMsg)

            # Parse out logging type and hand off to appropriate logger
            if jsonMsg.get("actuator_msg_type").get("logging").get("log_type") == "IEM":
                self._log_debug("_processMsg msg_type:Logging IEM")
                IEMlogger(jsonMsg)

            # ...Handle other types of logging
            
        except Exception as ex:
            # Log it and restart the whole process when a failure occurs
            logger.exception("LoggingMsgHandler restarting")

        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(0, self._priority, self.run, ())
        self._log_debug("Finished thread")

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(LoggingMsgHandler, self).shutdown()