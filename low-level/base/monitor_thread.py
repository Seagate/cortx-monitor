"""
 ****************************************************************************
 Filename:          monitor_thread.py
 Description:       Base classes used for scheduling thread execution 
                    in modules.
 Creation Date:     02/09/2015
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

import time
import abc

from utils.service_logging import logger
from sched import scheduler
from exceptions import NotImplementedError

class MonitorThread(object):
    """Base Class for all Monitoring Processes"""
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        super(MonitorThread, self).__init__()        

    @abc.abstractmethod
    def initialize(self):
        """Initialize the monitoring process"""
        raise NotImplementedError("Subclasses should implement this!")

    @abc.abstractmethod
    def run(self):
        """Periodically run the monitoring process"""
        raise NotImplementedError("Subclasses should implement this!")
        
    

class ScheduledMonitorThread(MonitorThread):
    """A monitoring process with an internal scheduler"""

    def __init__(self, module_name, priority):
        super(ScheduledMonitorThread, self).__init__()

        self._scheduler   = scheduler(time.time, time.sleep)
        self._module_name = module_name
        self._priority    = priority

    def initialize(self, conf_reader):
        """Initialize the monitoring thread"""
        # Set the configuration file reader located in /etc/sspl-ll.conf
        self._conf_reader = conf_reader
        
        # Set the scheduler to fire the thread right away
        self._scheduler.enter(1, self._priority, self.run, ())        
        
    def start(self):
        """Run the scheduler"""
        self._scheduler.run()

    def _cleanup_and_stop(self):
        """Clean out the remainder of events from the scheduler queue."""
        logger.info("Shutting down monitoring thread for '%s'",
                    self._module_name)
        for event in self._scheduler.queue:
            try:
                self._scheduler.cancel(event)
            except ValueError:
                # Being shut down so ignore
                pass

    def shutdown(self):
        """Clean up and shut down this monitor."""
        self._scheduler.enter(0, self._priority, self._cleanup_and_stop, ())
        logger.info("scheduling shut down for '%s'",
                    self._module_name)
 
    def getConf_reader(self):
        return self._conf_reader
    
        

