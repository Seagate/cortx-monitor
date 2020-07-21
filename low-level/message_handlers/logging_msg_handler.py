"""
 ****************************************************************************
 Filename:          logging_msg_handler.py
 Description:       Message Handler for logging Messages
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

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import enabled_products

# Modules that receive messages from this module
from framework.amqp.egress_processor import EgressProcessor

from json_msgs.messages.actuators.ack_response import AckResponseMsg


class LoggingMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for logging Messages"""

    MODULE_NAME = "LoggingMsgHandler"
    PRIORITY    = 2

    # Section and keys in configuration file
    LOGGINGMSGHANDLER   = MODULE_NAME.upper()
    IEM_ROUTING_ENABLED = 'iem_routing_enabled'
    IEM_LOG_LOCALLY     = 'iem_log_locally'


    @staticmethod
    def name():
        """ @return: name of the module."""
        return LoggingMsgHandler.MODULE_NAME

    def __init__(self):
        super(LoggingMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        # Flag to indicate suspension of module
        self._suspended = False

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(LoggingMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(LoggingMsgHandler, self).initialize_msgQ(msgQlist)

        # Read in configuration values
        self._conf_reader = conf_reader
        self._read_config()
        self._import_products(product)

    def _import_products(self, product):
        """Import classes based on which product is being used"""
        if product.lower() in [x.lower() for x in enabled_products]:
            from loggers.impl.iem_logger import IEMlogger
            self._iem_logger = IEMlogger(self._conf_reader)

    def run(self):
        """Run the module periodically on its own thread."""
        #self._set_debug(True)
        #self._set_debug_persist(True)
        self._log_debug("Start accepting requests")

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(20, self._priority, self.run, ())
            return

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
            logger.exception(f"LoggingMsgHandler restarting: {ae}")

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger"""
        self._log_debug(f"_process_msg, jsonMsg: {jsonMsg}")

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        uuid = None
        if jsonMsg.get("sspl_ll_msg_header") is not None and \
           jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            self._log_debug(f"_process_msg, uuid: {uuid}")

        log_type = jsonMsg.get("actuator_request_type").get("logging").get("log_type")

        result = "N/A"

        # Disabled for LDR_R1
        # if log_type == "IEM":
        #     self._log_debug("_process_msg, msg_type: IEM")
        #     if self._iem_log_locally == "true":
        #         result = self._iem_logger.log_msg(jsonMsg)
        #         self._log_debug(f"Log IEM results: {result}")

        if log_type == "HDS":
            # Retrieve the serial number of the drive
            self._log_debug("_process_msg, msg_type: HDS")
            log_msg = jsonMsg.get("actuator_request_type").get("logging").get("log_msg")

            # Parse out the json data section in the IEM and replace single quotes with double
            json_data = json.loads(str('{' + log_msg.split('{')[1]).replace("'", '"'))

            serial_number = json_data.get("serial_number")
            status = json_data.get("status")
            reason = json_data.get("reason")
            self._log_debug(f"_processMsg, serial_number: {serial_number}, status:{status}, reason: {reason}")

            # Send a message to the disk manager handler to create and transmit json msg
            internal_json_msg = json.dumps(
                 {"sensor_response_type" : "disk_status_HDS",
                  "object_path" : "HDS",
                  "status" : status,
                  "reason" : reason,
                  "serial_number" : serial_number
                 })

            # Send the event to disk message handler to generate json message
            self._write_internal_msgQ("DiskMsgHandler", internal_json_msg)

            # Disabled for LDR_R1
            # Hand off to the IEM logger
            # result = self._iem_logger.log_msg(jsonMsg)

            # Send ack about logging msg
            ack_msg = AckResponseMsg(log_type, result, uuid).getJson()
            self._write_internal_msgQ(EgressProcessor.name(), ack_msg)

        # ... handle other logging types

        # Disabled for LDR_R1
        # Route the IEM if enabled
        #if self._iem_routing_enabled == "true":
        #    self._route_IEM(jsonMsg)

    def _route_IEM(self, jsonMsg):
        # Send the IEM to the logging msg handler to be processed

        # Get the optional log_level if it exists in msg
        if jsonMsg.get("actuator_request_type").get("logging").get("log_level") is not None:
            log_level = jsonMsg.get("actuator_request_type").get("logging").get("log_level")
        else:
            log_level = "LOG_INFO"

        # Get the message to log in format "IEC: EVENT_CODE: EVENT_STRING: JSON DATA"
        log_msg = f"{log_level} {jsonMsg.get('actuator_request_type').get('logging').get('log_msg')}"

        internal_json_msg = json.dumps(
                 {"message": {
                    "IEM_routing": {
                        "log_msg": log_msg
                        }
                    }
                 })
        # Send the IEM to EgressProcessor to be routed to another IEM listener
        self._write_internal_msgQ(EgressProcessor.name(), internal_json_msg)

    def _read_config(self):
        """Read in configuration values"""
        try:
            self._iem_routing_enabled = self._conf_reader._get_value_with_default(self.LOGGINGMSGHANDLER,
                                                                 self.IEM_ROUTING_ENABLED,
                                                                 'false')
            self._iem_log_locally     = self._conf_reader._get_value_with_default(self.LOGGINGMSGHANDLER,
                                                                 self.IEM_LOG_LOCALLY,
                                                                 'true')
            logger.info(f"IEM routing enabled: {str(self._iem_routing_enabled)}")
            logger.info(f"IEM log locally: {str(self._iem_log_locally)}")
        except Exception as ex:
            logger.exception(f"_read_config: {ex}")

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(LoggingMsgHandler, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(LoggingMsgHandler, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(LoggingMsgHandler, self).shutdown()
