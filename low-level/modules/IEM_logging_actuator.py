"""
 ****************************************************************************
 Filename:          IEM_logging_actuator.py
 Description:       Handles IEM logging actuator requests
 Creation Date:     02/18/2015
 Author:            Jake Abernathy

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

import syslog
import os

from base.monitor_thread import ScheduledMonitorThread
from base.internal_msgQ import InternalMsgQ
from utils.service_logging import logger

class IEMloggingProcessor(ScheduledMonitorThread, InternalMsgQ):
    
    MODULE_NAME = "IEMloggingProcessor"
    PRIORITY    = 2

    # Section and keys in configuration file
    IEMLOGGINGPROCESSOR = MODULE_NAME.upper()
    EXCHANGE_NAME       = 'exchange_name'

    @staticmethod
    def name():
        """ @return name of the monitoring module."""
        return IEMloggingProcessor.MODULE_NAME
    
    def __init__(self):
        super(IEMloggingProcessor, self).__init__(self.MODULE_NAME,
                                                      self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(IEMloggingProcessor, self).initialize(conf_reader)
        
        # Initialize internal message queues for this module
        super(IEMloggingProcessor, self).initializeMsgQ(msgQlist)
        
    def run(self):
        """Run the module periodically on its own thread. """
        logger.info("Starting thread for '%s'", self.name())
        
        try:
            # Block on message queue until it contains an entry then log it
            logMsg = self._readMyMsgQ().encode('utf8')
            syslog.syslog(logMsg)
            logger.info("IEMloggingProcessor, run logMsg: %s" % logMsg)
            
        except Exception as ex:
            # Log it and restart the whole process when a failure occurs      
            logger.exception("IEMloggingProcessor Exception")            
        
        # TODO: poll_time = int(self._get_monitor_config().get(MONITOR_POLL_KEY))
        self._scheduler.enter(0, self._priority, self.run, ())    
        logger.info("Finished thread for '%s'", self.name())
        
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(IEMloggingProcessor, self).shutdown()
        
