"""
 ****************************************************************************
 Filename:          real_stor_encl_msg_handler.py
 Description:       Message Handler for processing enclosure level sensor data
 Creation Date:     06/19/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2019/06/19 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json

from zope.component import queryUtility

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from json_msgs.messages.sensors.realstor_psu_data import RealStorPSUDataMsg
from json_msgs.messages.sensors.realstor_fan_data import RealStorFandataMsg
from json_msgs.messages.sensors.realstor_controller_data import RealStorControllerDataMsg
from message_handlers.logging_msg_handler import LoggingMsgHandler
from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

class RealStorEnclMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for processing real store sensor events and generating
        alerts in the RabbitMQ channel"""

    MODULE_NAME = "RealStorEnclMsgHandler"
    # TODO increase the priority
    PRIORITY = 2

    @staticmethod
    def name():
        """ @return: name of the module."""
        return RealStorEnclMsgHandler.MODULE_NAME

    def __init__(self):
        super(RealStorEnclMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(RealStorEnclMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorEnclMsgHandler, self).initialize_msgQ(msgQlist)

        self._psu_sensor_message = None
        self._fan_sensor_message = None
        self._controller_sensor_message = None

    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Start accepting requests")

        try:
            # Block on message queue until it contains an entry
            json_msg = self._read_my_msgQ()
            if json_msg is not None:
                self._process_msg(json_msg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                json_msg = self._read_my_msgQ()
                if json_msg is not None:
                    self._process_msg(json_msg)

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception("RealStorEnclMsgHandler restarting: %s" % ae)

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, json_msg):
        """Parses the incoming message and generate the desired data message"""
        self._log_debug("RealStorEnclMsgHandler, _process_msg, json_msg: %s" % json_msg)

        if json_msg.get("sensor_request_type") is not None and \
            json_msg.get("sensor_request_type").get("enclosure_alert") is not None:
            internal_sensor_request = json_msg.get("sensor_request_type").get("enclosure_alert").get("status")
            if internal_sensor_request:
                # parses the internal json request coming from any RealStor sensor
                sensor_type = json_msg.get("sensor_request_type").get("enclosure_alert").get("sensor_type")
                self._propagate_alert(json_msg, sensor_type)
            else:
                # serves the request coming from sspl CLI
                sensor_type = json_msg.get("sensor_request_type").get("enclosure_alert").get("sensor_type")
                if sensor_type == "enclosure_psu_alert":
                    # return the lastly saved json message as response for sspl CLI request
                    if self._psu_sensor_message:
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), self._psu_sensor_message)
                    else:
                        self._log_debug("No psu sensor past data found")
                if sensor_type == "enclosure_fan_alert":
                    # return the lastly saved json message as response for sspl CLI request
                    if self._fan_sensor_message:
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), self._fan_sensor_message)
                    else:
                        self._log_debug("No fan sensor past data found")
                if sensor_type == "enclosure_controller_alert":
                    # return the lastly saved json message as response for sspl CLI request
                    if self._controller_sensor_message:
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), self._controller_sensor_message)
                    else:
                        self._log_debug("No controller sensor past data found")
        else:
            logger.exception("_process_msg, Not a valid sensor request format")

    def _propagate_alert(self, json_msg, sensor_type):
        """extracts specific field from json message and propagates json message based on sensor type"""
        self._log_debug("RealStorEnclMsgHandler, _propagate_alert, json_msg %s" % json_msg)

        resource_type = json_msg.get("sensor_request_type").get("enclosure_alert").get("resource_type")

        if resource_type == "fru":
            alert_type = json_msg.get("sensor_request_type").get("enclosure_alert").get("alert_type")
            info = json_msg.get("sensor_request_type").get("info")
            extended_info = json_msg.get("sensor_request_type").get("extended_info")
            self._log_debug("_processMsg, sensor_type: %s" % sensor_type)

            if sensor_type == "enclosure_fan_alert":
                self._generate_fan_alert(json_msg, alert_type, resource_type, info, extended_info)

            if sensor_type == "enclosure_psu_alert":
                self._generate_psu_alert(json_msg, alert_type, resource_type, info, extended_info)

            if sensor_type == "enclosure_controller_alert":
                self._generate_controller_alert(json_msg, alert_type, resource_type, info, extended_info)

    def _generate_psu_alert(self, json_msg, alert_type, resource_type, info, extended_info):
        """parses the json message, also validates it and then send it to the RabbitMQ egress processor"""

        self._log_debug("RealStorEnclMsgHandler, _generate_psu_alert, json_msg %s" % json_msg)

        real_stor_psu_data_msg = RealStorPSUDataMsg(alert_type, resource_type, info, extended_info)
        json_msg = real_stor_psu_data_msg.getJson()
        # save the json message in memory to serve sspl CLI sensor request
        self._psu_sensor_message = json_msg
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def _generate_fan_alert(self, json_msg, alert_type, resource_type, info, extended_info):
        """parses the json message, also validates it and then send it to the RabbitMQ egress processor"""

        self._log_debug("RealStorEnclMsgHandler, _generate_fan_alert, json_msg %s" % json_msg)

        real_stor_fan_data_msg = RealStorFandataMsg(alert_type, resource_type, info, extended_info)
        json_msg = real_stor_fan_data_msg.getJson()
        # save the json message in memory to serve sspl CLI sensor request
        self._fan_sensor_message = json_msg
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def _generate_controller_alert(self, json_msg, alert_type, resource_type, info, extended_info):
        """parses the json message, also validates it and then send it to the RabbitMQ egress processor"""

        self._log_debug("RealStorEnclMsgHandler, _generate_controller_alert, json_msg %s" % json_msg)

        real_stor_controller_data_msg = RealStorControllerDataMsg(alert_type, resource_type, info, extended_info)
        json_msg = real_stor_controller_data_msg.getJson()
        # save the json message in memory to serve sspl CLI sensor request
        self._controller_sensor_message = json_msg
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorEnclMsgHandler, self).shutdown()

