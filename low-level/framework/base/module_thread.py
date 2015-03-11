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
"""

import time
import abc
import json

from sched import scheduler
from exceptions import NotImplementedError
from debug import Debug


class ModuleThread(object):
    """Base Class for all Module Threads"""
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        super(ModuleThread, self).__init__()        

    @abc.abstractmethod
    def initialize(self):
        """Initialize the module thread"""
        raise NotImplementedError("Subclasses should implement this!")

    @abc.abstractmethod
    def run(self):
        """Periodically run the module thread"""
        raise NotImplementedError("Subclasses should implement this!")


class ScheduledModuleThread(ModuleThread, Debug):
    """A module thread with an internal scheduler"""

    def __init__(self, module_name, priority):
        super(ScheduledModuleThread, self).__init__()

        self._scheduler   = scheduler(time.time, time.sleep)
        self._module_name = module_name
        self._priority    = priority
        self._running     = False

    def initialize(self, conf_reader):
        """Initialize the monitoring thread"""
        # Set the configuration file reader located in /etc/sspl-ll.conf
        self._conf_reader = conf_reader
        
        # Set the scheduler to fire the thread right away
        self._scheduler.enter(1, self._priority, self.run, ())     
        
        # Set running to True signifying the thread is active
        set_running = True   
        
    def start(self):
        """Run the scheduler"""
        self._running = True
        self._scheduler.run()

    def _cleanup_and_stop(self):
        """Clean out the remainder of events from the scheduler queue."""
        self._log_debug("_cleanup_and_stop")
        for event in self._scheduler.queue:
            try:
                self._scheduler.cancel(event)
            except ValueError:
                # Being shut down so ignore
                pass

    def shutdown(self):
        """Clean up and shut down this monitor."""
        self._running = False
        # Give the module a few seconds to close down RabbitMQ connections if they're open
        self._scheduler.enter(2, self._priority, self._cleanup_and_stop, ())
        self._log_debug("Scheduling shut down")
 
    def _getConf_reader(self):
        return self._conf_reader
    
    def is_running(self):
        return self._running

