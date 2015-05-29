"""
 ****************************************************************************
 Filename:          node_msg_handler.py
 Description:       Message Handler for generic node requests and generating
                    host update messages on a regular interval
 Creation Date:     05/20/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import json
import time
import psutil
import syslog
import socket

from actuators.IService import IService
from actuators.ILogin import ILogin

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

from json_msgs.messages.sensors.host_update import HostUpdateMsg
from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor 

from zope.component import queryUtility


class NodeMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for generic node requests and generating
        host update messages on a regular interval"""

    MODULE_NAME = "NodeMsgHandler"
    PRIORITY    = 2


    @staticmethod
    def name():
        """ @return: name of the module."""
        return NodeMsgHandler.MODULE_NAME

    def __init__(self):
        super(NodeMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(NodeMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(NodeMsgHandler, self).initialize_msgQ(msgQlist)

    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Start accepting requests")

        #self._set_debug(True)
        #self._set_debug_persist(True)

        try:
            # See if the message queue contains an entry and process
            jsonMsg = self._read_my_msgQ_noWait()
            if jsonMsg is not None:
                self._process_msg(jsonMsg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                jsonMsg = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._process_msg(jsonMsg)

            self._generate_host_update()

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.exception("NodeMsgHandler restarting")

        self._scheduler.enter(10, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger"""
        self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

        if isinstance(jsonMsg, dict) == False:
            jsonMsg = json.loads(jsonMsg)

        if jsonMsg.get("actuator_request_type").get("login_controller") is not None:
            self._log_debug("_processMsg, msg_type: login_controller")

            # Query the Zope GlobalSiteManager for an object implementing IService
            service_actuator = queryUtility(ILogin)()
            self._log_debug("_process_msg, service_actuator name: %s" % service_actuator.name())
            result = service_actuator.perform_request(jsonMsg)

            self._log_debug("_processMsg, result: %s" % result)

            # TODO: Create a service LoginResults message and send it out
            service_name = "LoginResults"
            jsonMsg = ServiceWatchdogMsg(service_name, result).getJson()
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

        # ... handle other service message types

    def _generate_host_update(self):
        """Create & transmit a host update message as defined
            by the sensor response json schema"""

        # First calls gethostname to see if it returns something that looks like a host name, 
        # if not then get the host by address
        if socket.gethostname().find('.') >=0:
            host_id = socket.gethostname()
        else:
            host_id = socket.gethostbyaddr(socket.gethostname())[0]

        local_time      = str(time.localtime())
        boot_time       = "test"
        up_time         = psutil.boot_time()
        uname           = str(os.uname())
        free_mem        = 1234
        free_mem_units  = "GB"
        total_mem       = 1234
        total_mem_units = "GB"
        logged_in_users = ["Ted", "Mike", "Joe"]
        process_count   = 1234
        running_process_count = 1234
        
#         jsonMsg = HostUpdateMsg(host_id, local_time, boot_time, up_time,
#                        uname, free_mem, free_mem_units, total_mem,
#                        total_mem_units, logged_in_users, process_count,
#                        running_process_count).getJson()
#         self._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(NodeMsgHandler, self).shutdown()