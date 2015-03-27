"""
 ****************************************************************************
 Filename:          systemd_msg_handler.py
 Description:       Message Handler for systemd Messages
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

import json
import syslog

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

from actuators.impl.systemd_service import SystemdService
from json_msgs.messages.actuators.systemd_service import SystemdServiceMsg
from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor 

class SystemdMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for logging Messages"""

    MODULE_NAME = "SystemdMsgHandler"
    PRIORITY    = 2


    @staticmethod
    def name():
        """ @return: name of the module."""
        return SystemdMsgHandler.MODULE_NAME

    def __init__(self):
        super(SystemdMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(SystemdMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(SystemdMsgHandler, self).initialize_msgQ(msgQlist)

    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Start accepting requests")

        try:
            # Block on message queue until it contains an entry
            jsonMsg = self._read_my_msgQ()
            if jsonMsg is not None:
                self._process_msg(jsonMsg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                jsonMsg = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._process_msg(jsonMsg)

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.exception("SystemdMsgHandler restarting")

        self._scheduler.enter(0, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger"""
        self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

        if isinstance(jsonMsg, dict) == False:
            jsonMsg = json.loads(jsonMsg)

        # Handle service start, stop, restart, status requests
        if jsonMsg.get("actuator_request_type").get("systemd_service") is not None:
            self._log_debug("_processMsg, msg_type: systemd_service")

            #TODO: Create a factory class that returns the desired actuator object
            #      based upon whether systemd or other service is available
            systemd_service = SystemdService()
            service_name, result = systemd_service.perform_service_request(jsonMsg)

            self._log_debug("_processMsg, service_name: %s, result: %s" %
                            (service_name, result))

            # Create an actuator response and send it out
            jsonMsg = SystemdServiceMsg(service_name, result).getJson()        
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

        # ... handle other systemd message types


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(SystemdMsgHandler, self).shutdown()