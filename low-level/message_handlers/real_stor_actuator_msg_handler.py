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
  Description:       Message Handler for controlling the RealStor actuator
 ****************************************************************************
"""

import json
import time

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.base.sspl_constants import enabled_products
from framework.utils.conf_utils import GLOBAL_CONF, RELEASE, SSPL_CONF, Conf
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.realstor_actuator_response import \
    RealStorActuatorMsg
from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor


class RealStorActuatorMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for controlling the RealStor actuator"""

    MODULE_NAME = "RealStorActuatorMsgHandler"
    PRIORITY    = 2

    SYS_INFORMATION = 'SYSTEM_INFORMATION'
    SETUP = 'setup'

    UNSUPPORTED_REQUEST = "Unsupported Request"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": [
                        "ServiceMsgHandler",
                        "RabbitMQegressProcessor",
                        "DiskMsgHandler"
                    ],
                    "rpms": []
    }


    @staticmethod
    def name():
        """ @return: name of the module."""
        return RealStorActuatorMsgHandler.MODULE_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return RealStorActuatorMsgHandler.DEPENDENCIES

    def __init__(self):
        super(RealStorActuatorMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        # Flag to indicate suspension of module
        self._suspended = False

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(RealStorActuatorMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorActuatorMsgHandler, self).initialize_msgQ(msgQlist)

        self._real_stor_actuator    = None

        self._import_products(product)
        self.setup = Conf.get(GLOBAL_CONF, f"{RELEASE}>{self.SETUP}","ssu")

    def _import_products(self, product):
        """Import classes based on which product is being used"""
        if product.lower() in [x.lower() for x in enabled_products]:
            from zope.component import queryUtility
            self._queryUtility = queryUtility

    def run(self):
        """Run the module periodically on its own thread."""
        self._set_debug(True)
        self._set_debug_persist(True)

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(1, self._priority, self.run, ())
            return
        self._log_debug("Start accepting requests")

        try:
            # Block on message queue until it contains an entry
            jsonMsg, _ = self._read_my_msgQ()
            if jsonMsg is not None:
                self._process_msg(jsonMsg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                jsonMsg, _ = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._process_msg(jsonMsg)

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception(f"RealStorActuatorMsgHandler restarting: {ae}")

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and handles appropriately"""
        self._log_debug(f"RealStorActuatorMsgHandler, _process_msg, jsonMsg: {jsonMsg}")

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        # Parse out the uuid so that it can be sent back in Ack message
        uuid = None
        if jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            self._log_debug(f"_processMsg, uuid: {uuid}")

        logger.debug(f"RealStorActuatorMsgHandler: _process_msg: jsonMsg: {jsonMsg}")
        if jsonMsg.get("actuator_request_type").get("storage_enclosure").get("enclosure_request") is not None:
            enclosure_request = jsonMsg.get("actuator_request_type").get("storage_enclosure").get("enclosure_request")
            self._log_debug(f"_processMsg, enclosure_request: {enclosure_request}")
            logger.debug(f"RealStorActuatorMsgHandler: _process_msg: INSIDE: jsonMsg: {jsonMsg}")

            # Parse out the request field in the enclosure_request
            (request, fru) = enclosure_request.split(":", 1)
            request = request.strip()
            fru = fru.strip()

            if self._real_stor_actuator is None:
                try:
                    from actuators.impl.generic.realstor_encl import RealStorActuator
                    self._real_stor_actuator = RealStorActuator()
                except ImportError as e:
                    logger.warn("RealStor Actuator not loaded")
                    return

            # Perform the request and get the response
            real_stor_response = self._real_stor_actuator.perform_request(jsonMsg)
            self._log_debug(f"_process_msg, RealStor response: {real_stor_response}")

            json_msg = RealStorActuatorMsg(real_stor_response, uuid).getJson()
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RealStorActuatorMsgHandler, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RealStorActuatorMsgHandler, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorActuatorMsgHandler, self).shutdown()
