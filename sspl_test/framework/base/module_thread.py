# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Base classes used for scheduling thread execution
                    in modules.
 ****************************************************************************
"""

import time
import abc
import json

from sched import scheduler
from cortx.sspl.sspl_test.framework.base.debug import Debug


class ModuleThread(metaclass=abc.ABCMeta):
    """Base Class for all Module Threads"""

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

    def start(self):
        """Run the scheduler"""
        self._running = True
        self._scheduler.run()

    def _cleanup_and_stop(self):
        """Clean out the remainder of events from the scheduler queue."""
        self._log_debug("last module calling _cleanup_and_stop thread scheduler")
        for event in self._scheduler.queue:
            try:
                self._scheduler.cancel(event)
            except ValueError:
                # Being shut down so ignore
                pass
        self._log_debug("Thread scheduler cancelled successfully")

    def shutdown(self):
        """Clean up and shut down this monitor."""
        self._running = False

        # Give the module a few seconds to close down
        self._scheduler.enter(10, self._priority, self._cleanup_and_stop, ())
        self._log_debug("Scheduling shut down")

    def _getConf_reader(self):
        return self._conf_reader

    def is_running(self):
        return self._running
