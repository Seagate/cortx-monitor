"""All Monitoring threads base classes"""

import time
import abc

from utils.service_logging import logger
from sched import scheduler


class MonitorThread(object):
    """Base Class for all Monitoring Processes"""
    __metaclass__ = abc.ABCMeta

    def __init__(self):
        pass

    @abc.abstractmethod
    def initialize(self):
        """Initialize the monitoring process"""
        pass

    @abc.abstractmethod
    def run(self):
        """Periodically run the monitoring process"""
        pass


class ScheduledMonitorThread(MonitorThread):
    """A monitoring process with an internal scheduler"""

    def __init__(self, module_name, priority):
        super(ScheduledMonitorThread, self).__init__()

        self._scheduler   = scheduler(time.time, time.sleep)
        self._module_name = module_name
        self._priority    = priority

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

    def initialize(self, rabbitMsgQ, conf_reader):
        """Initialize the monitoring thread"""
        super(ScheduledMonitorThread, self).initialize()        
        self._rabbitMsgQ     = rabbitMsgQ
        self._conf_reader    = conf_reader
        self._scheduler.enter(1, self._priority, self.run, ())
    
    def run(self):
        """Periodically run the monitor process"""
        super(ScheduledMonitorThread, self).run()
    
    def getConf_reader(self):
        return self._conf_reader
    
    def isRabbitMsgQempty(self):
        return self._rabbitMsgQ.empty()
    
    def _readRabbitMQ(self):
        """Reads a json message from the queue placed by another thread"""
        jsonMsg = {}
        if not self._rabbitMsgQ.empty():
            jsonMsg = self._rabbitMsgQ.get_nowait()
            logger.info("readRabbitMQ: From %s, Msg:%s" % (self.name(), jsonMsg))
        else:
            logger.info("readRabbitMQ: From %s: rabbitMsgQ is empty" % self.name())
        return jsonMsg
    
    def _writeRabbitMQ(self, jsonMsg):
        """writes a json message to the RabbitMsgQ to be transmitted"""
        try:
            logger.info("writeRabbitMQ: From %s, Msg:%s" % (self.name(), jsonMsg))
            self._rabbitMsgQ.put(jsonMsg)
        except Exception as ex:
            logger.exception("writeRabbitMQ: %s" % ex)
    
        

