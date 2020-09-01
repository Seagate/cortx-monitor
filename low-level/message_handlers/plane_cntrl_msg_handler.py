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
  Description:       Message Handler for service request messages
 ****************************************************************************
"""
import json

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import cs_legacy_products

# Modules that receive messages from this module
from framework.rabbitmq.plane_cntrl_rmq_egress_processor import PlaneCntrlRMQegressProcessor
from json_msgs.messages.actuators.ack_response import AckResponseMsg


class PlaneCntrlMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for plane controller request messages"""

    MODULE_NAME = "PlaneCntrlMsgHandler"
    PRIORITY    = 2


    @staticmethod
    def name():
        """ @return: name of the module."""
        return PlaneCntrlMsgHandler.MODULE_NAME

    def __init__(self):
        super(PlaneCntrlMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(PlaneCntrlMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(PlaneCntrlMsgHandler, self).initialize_msgQ(msgQlist)

        self._import_products(product)

        self._sedOpDispatch = None

    def _import_products(self, product):
        """Import classes based on which product is being used"""
        if product in cs_legacy_products:
            from sedutil.sedDispatch import SedOpDispatch
            self._SedOpDispatch = SedOpDispatch
            self._SedOpDispatch.setLogger(logger)

    def run(self):
        """Run the module on its own thread blocking for incoming messages."""
        #self._set_debug(True)
        #self._set_debug_persist(True)

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
            logger.exception(f"PlaneCntrlMsgHandler restarting: {str(ae)}")

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and process"""

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        # Parse json msg into usable fields
        success = self._parse_jsonMsg(jsonMsg)
        if not success:
            response = "An error occurred parsing JSON fields"
            self._send_response(response)
            return

        status   = -1
        response = "N/A"
        errors   = "N/A"
        hostname = "N/A"
        try:
            self._sedOpDispatch = self._SedOpDispatch(self._command, self._parameters, self._arguments)
            status = self._sedOpDispatch.status

            # Don't continue on init errors, invalid command or doesn't apply to this node
            if self._sedOpDispatch.status != 0:
                if self._sedOpDispatch.status == 2:
                    self._log_debug("_process_msg, request is not for this node, ignoring.")
                else:
                    errors = self._sedOpDispatch.errors
                    self._log_debug(f"_process_msg, status: {str(self._sedOpDispatch.status)}, errors: {str(errors)}")
                return

            # Let the egress processor know the current task being worked
            self._write_internal_msgQ(PlaneCntrlRMQegressProcessor.name(), jsonMsg)

            hostname = self._sedOpDispatch.hostname

            # Run the command with the parameters and arguments and retrive the response and any errors
            status   = self._sedOpDispatch.run()
            response = self._sedOpDispatch.output
            errors   = self._sedOpDispatch.errors

            self._log_debug(f"PlaneCntrlMsgHandler, _process_msg, status: {str(status)},     \
                              command: {str(self._command)}, parameters: {str(self._parameters)}, \
                              args: {str(self._arguments)}")
            self._log_debug(f"PlaneCntrlMsgHandler, _process_msg, response: {str(response)}")
            self._log_debug(f"PlaneCntrlMsgHandler, _process_msg, errors: {str(errors)}")
        except Exception as ae:
            errors = str(ae)
            logger.warn(f"PlaneCntrlMsgHandler, _process_msg exception: {errors}")
            response = "There was an error processing the request.  Please refer to the logs for details."

        # No need to enable self._sedOpDispatch.interrupt() in the shutdown()
        self._sedOpDispatch = None

        # Transmit the response back as an Ack json msg
        self._send_response(status, hostname, response, errors)

    def _send_response(self, status, hostname, response, errors):
        """Transmit the response back as an Ack json msg"""
        ack_type = {}
        ack_type["hostname"], ack_type["command"], ack_type["parameters"], ack_type["status"], \
            ack_type["errors"] = str(hostname, 'utf-8'), self._command, self._parameters,  \
            status, str(errors, 'utf-8')
        ack_msg = AckResponseMsg(json.dumps(ack_type), \
                                 str(response), self._uuid).getJson()
        self._write_internal_msgQ(PlaneCntrlRMQegressProcessor.name(), ack_msg)

    def _parse_jsonMsg(self, jsonMsg):
        """Parse json msg into usable fields"""
        try:
            # Parse out the uuid so that it can be sent back in Ack message
            self._uuid = None
            if jsonMsg.get("sspl_ll_msg_header") is not None and \
               jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
                self._uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")

            # Parse out values from msg
            self._command    = jsonMsg.get("actuator_request_type").get("plane_controller").get("command")
            self._parameters = jsonMsg.get("actuator_request_type").get("plane_controller").get("parameters")
            self._arguments  = jsonMsg.get("actuator_request_type").get("plane_controller").get("arguments")

            # Ignore incorrectly formatted messages
            if self._command is None:
                logger.warn("PlaneCntrlMsgHandler, _parse_jsonMsg, command is none")
                logger.warn(f"PlaneCntrlMsgHandler, _process_msg, command: {str(self._command)}")
                return False

            return True
        except Exception as ae:
            logger.warn(f"PlaneCntrlMsgHandler, _parse_jsonMsg: {str(ae)}")
            return False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        logger.info("PlaneCntrlMsgHandler, thread shutting down")

        # Cleanup
        super(PlaneCntrlMsgHandler, self).shutdown()

        # Interrupt any current SED operations
        if self._sedOpDispatch is not None:
            try:
                logger.info("PlaneCntrlMsgHandler, calling sedOpDispatch.interrupt()")
                self._sedOpDispatch.interrupt()
            except Exception as ae:
                logger.warn(f"PlaneCntrlMsgHandler, shutdown, _sedOpDispatch.interrupt exception: {str(ae)}")
