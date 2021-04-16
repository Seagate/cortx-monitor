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

import abc
import json
import threading
import time
from sched import scheduler
from .debug import Debug
from framework.utils.service_logging import logger

class DependencyState(object):
    DEPS_STARTING = 0
    DEPS_FAILED = 2
    DEPS_SUCCESS = 4

class InitState(object):
    INITIALIZING = 0
    INIT_FAILED = 1
    INIT_SUCCESS = 2

class SensorThreadState(object):
    WAITING = 0
    RUNNING = 1
    FAILED = 3

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

    # Module thread states
    ACTIVE = 1
    SUSPENDED = 2
    HALTED = 3

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

    def start_thread(self, conf_reader, msgQlist, product):
        self.initialize(conf_reader, msgQlist, product)
        self.start()

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

    def suspend(self):
        logger.debug("suspend() of {0} is called".format(self.name()))

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        logger.debug("resume() of {0} is called".format(self.name()))

    def get_state(self):
        """Returns the current state of module thread"""
        current_state = None
        if self.is_running() and not self.is_suspended():
            current_state = ScheduledModuleThread.ACTIVE
        elif self.is_running() and self.is_suspended():
            current_state = ScheduledModuleThread.SUSPENDED
        elif not self.is_running():
            current_state = ScheduledModuleThread.HALTED
        return current_state

    def is_suspended(self):
        """Returns True if the module thread is suspended. False otherwise"""
        logger.debug("is_suspended() of {0} is called".format(self.name()))

class SensorThread(ScheduledModuleThread):
    SENSORTHREAD_INIT_WAIT_TIMEOUT = 300
    SENSORTHREAD_INIT_WAIT_INTERVAL = 10

    def __init__(self, module_name, priority):
        super(SensorThread, self).__init__(module_name, priority)

        self.lock = threading.Lock()

        self.remaining_dependees = set()
        self.num_failed_dependees = 0
        self.waiting_dependers = set()
        self.deps_status = DependencyState.DEPS_STARTING

        self.init_status = InitState.INITIALIZING

        self.has_timed_out = False
        self.current_timeout_wait = 0

        self.status = SensorThreadState.WAITING


    def initialize(self, conf_reader):
        """Initialize the monitoring thread"""
        # Set the configuration file reader located in /etc/sspl-ll.conf
        self._conf_reader = conf_reader

        # Set the scheduler to fire the thread right away
        self._scheduler.enter(1, self._priority, self.check_and_run, ())

    def get_thread_init_status(self):
        self.lock.acquire()
        s = self.status
        self.lock.release()

        return s

    def prepare(self, dependencies):
        logger.debug("{} depends on {}".format(
            self.__class__.__name__, [d.__class__.__name__ for d in dependencies]))

        self.remaining_dependees |= set(dependencies)
        for d in self.remaining_dependees:
            d.my_register(self)

    def my_register(self, depender):
        logger.debug("{} registering dependency on {}".format(
            depender.__class__.__name__, self.__class__.__name__))

        self.lock.acquire()
        self.waiting_dependers |= {depender}
        self.lock.release()


    def check_and_conclude_initialization(self):
        logger.debug("Begin {}.conclude_initializatio()".format(
            self.__class__.__name__))

        # Check that self.lock is held by the caller
        if self.lock.acquire(blocking=False):
            self.lock.release()
            logger.error("SensorThread.check_and_conclude_initialization() called"\
                " without acquiring lock. Returning immediately")
            return

        if self.status != SensorThreadState.WAITING:
            return

        # It is possible that self.event() is not called at all.
        if self.num_failed_dependees:
            self.deps_status = DependencyState.DEPS_FAILED
        elif not self.remaining_dependees:
            self.deps_status = DependencyState.DEPS_SUCCESS

        definitely_failed = \
                self.deps_status == DependencyState.DEPS_FAILED or \
                self.init_status == InitState.INIT_FAILED or \
                self.has_timed_out
        definitely_succeeded = \
                self.deps_status == DependencyState.DEPS_SUCCESS and \
                self.init_status == InitState.INIT_SUCCESS

        if (definitely_failed):
            self.status = SensorThreadState.FAILED
        elif (definitely_succeeded):
            self.status = SensorThreadState.RUNNING
        # else it remains as waiting

        if self.status != SensorThreadState.WAITING:
            for d in self.waiting_dependers:
                d.event(self, self.status == SensorThreadState.RUNNING)

        logger.debug("End {}.conclude_initializatio() with state {}".format(
            self.__class__.__name__, self.status))


    def event(self, dependee, running):
        logger.debug("event in {} by {} calling start() with status {}".format(
            self.__class__.__name__, dependee.__class__.__name__, running))

        self.lock.acquire()

        self.remaining_dependees -= {dependee}
        if running:
            pass
        else:
            self.num_failed_dependees += 1

        self.check_and_conclude_initialization()

        self.lock.release()


    def start_thread(self, conf_reader, msgQlist, product):
        logger.debug("Begin {}.start_thread()".format(self.__class__.__name__))
        status = self.initialize(conf_reader, msgQlist, product)

        self.lock.acquire()

        if status:
            self.init_status = InitState.INIT_SUCCESS
        else:
            self.init_status = InitState.INIT_FAILED

        self.check_and_conclude_initialization()

        self.lock.release()

        self.start()
        logger.debug("End {}.start_thread()".format(self.__class__.__name__))

    def check_and_run(self):
        logger.debug("Begin {}.should_run()".format(self.__class__.__name__))
        self.lock.acquire()

        self.current_timeout_wait += self.SENSORTHREAD_INIT_WAIT_INTERVAL
        if self.current_timeout_wait > self.SENSORTHREAD_INIT_WAIT_TIMEOUT:
            self.has_timed_out = True
        self.check_and_conclude_initialization()

        should_run = self.status == SensorThreadState.RUNNING
        self.lock.release()

        if not should_run:
            self._scheduler.enter(self.SENSORTHREAD_INIT_WAIT_INTERVAL,
                    self._priority, self.check_and_run, ())
        else:
            self._scheduler.enter(1, self._priority, self.run, ())

class ThreadException(Exception):
    """Generic Exception to handle Threads errors."""

    def __init__(self, module, message):
        """Handle error msg from thread modules."""
        self._module = module
        self._desc = message

    def __str__(self):
        """Returns formated error msg."""
        return "%s: error: %s" %(self._module, self._desc)
