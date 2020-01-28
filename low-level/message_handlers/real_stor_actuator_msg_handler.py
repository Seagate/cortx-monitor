"""
 ****************************************************************************
 Filename:          real_stor_actuator_msg_handler.py
 Description:       Message Handler for controlling the RealStor actuator
 Creation Date:     11/01/2019
 Author:            Pranav Risbud

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import enabled_products

from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from json_msgs.messages.sensors.realstor_actuator_response import RealStorActuatorSensorMsg


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

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(RealStorActuatorMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorActuatorMsgHandler, self).initialize_msgQ(msgQlist)

        self._real_stor_actuator    = None

        self._import_products(product)
        self.setup = self._conf_reader._get_value_with_default(self.SYS_INFORMATION, self.SETUP, "ssu")

    def _import_products(self, product):
        """Import classes based on which product is being used"""
        if product in enabled_products:
            from zope.component import queryUtility
            self._queryUtility = queryUtility

    def run(self):
        """Run the module periodically on its own thread."""
        self._set_debug(True)
        self._set_debug_persist(True)
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

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception("RealStorActuatorMsgHandler restarting: %s" % ae)

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and handles appropriately"""
        self._log_debug("RealStorActuatorMsgHandler, _process_msg, jsonMsg: %s" % jsonMsg)

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        # Parse out the uuid so that it can be sent back in Ack message
        uuid = None
        if jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            self._log_debug("_processMsg, uuid: %s" % uuid)

        logger.debug("RealStorActuatorMsgHandler: _process_msg: jsonMsg: {}".format(jsonMsg))
        if jsonMsg.get("actuator_request_type").get("storage_enclosure").get("enclosure_request") is not None:
            enclosure_request = jsonMsg.get("actuator_request_type").get("storage_enclosure").get("enclosure_request")
            self._log_debug("_processMsg, enclosure_request: %s" % enclosure_request)
            logger.debug("RealStorActuatorMsgHandler: _process_msg: INSIDE: jsonMsg: {}".format(jsonMsg))

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
                    json_msg = RealStorActuatorAckMsg(enclosure_request, RealStorActuatorMsgHandler.UNSUPPORTED_REQUEST, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
                    return

            # Perform the request and get the response
            real_stor_response = self._real_stor_actuator.perform_request(jsonMsg)
            self._log_debug("_process_msg, RealStor response: %s" % real_stor_response)

            json_msg = RealStorActuatorSensorMsg(real_stor_response, uuid).getJson()
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorActuatorMsgHandler, self).shutdown()

