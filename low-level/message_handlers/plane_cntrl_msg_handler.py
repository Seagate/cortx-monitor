"""
 ****************************************************************************
 Filename:          plane_cntrl_msg_handler.py
 Description:       Message Handler for service request messages
 Creation Date:     11/17/2016
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
import subprocess

from socket import gethostname

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

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

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(PlaneCntrlMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(PlaneCntrlMsgHandler, self).initialize_msgQ(msgQlist)

        self._host_name = gethostname() 
        logger.info("          Monitoring plane requests for: %s" % self._host_name)
        #logger.info("          HA Partner: %s" % self._sedutil_arg_parse.machineInfo.partner)

    def run(self):
        """Run the module periodically on its own thread."""
        #self._set_debug(True)
        #self._set_debug_persist(True)

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
            logger.exception("PlaneCntrlMsgHandler restarting: %s" % str(ae))

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger"""
        if isinstance(jsonMsg, dict) == False:
            jsonMsg = json.loads(jsonMsg)

        # Parse json msg into usable fields
        success = self._parse_jsonMsg(jsonMsg)
        if not success:
            response = "An error occurred parsing JSON fields"
            # Transmit the response back as an Ack json msg
            self._send_response(response)
            return

        # Convert SSPL's CLI to sedutils CLI (temporary as CLIs differ)
        self.ssplCLI_to_sedutilsCLI_converter()

        # See if the msg applies to this node 
        if self._node_id != "None":
            applies_to_node = False
            for server in self._servers:
                if server in self._host_name:
                    applies_to_node = True
                    break
            if not applies_to_node:
                self._log_debug("_processMsg, does not apply to this node, ignoring.")              
                return

        logger.info("PlaneCntrlMsgHandler, _process_msg. msg_type: %s, plane request: %s" % \
                    (self._msg_type, self._plane_request))
        logger.info("PlaneCntrlMsgHandler, _process_msg, node_id: %s, drive_id: %s, debug_id: %s, raid_id: %s" % 
                    (self._node_id, self._drive_id, self._debug_id, self._raid_id))
        try:
            # Make a subprocess command into sedutil's CLI and capture the output (hopefully this will be in path later)
            cmd = "python /usr/lib64/python2.6/site-packages/sedutil/sedutil.py %s %s" % \
                        (self._sedutils_cmd, self._sedutils_params)
            self._log_debug("_process_msg, sedutils cmd: %s " % cmd)
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            output, errors = proc.communicate()
 
            if proc.wait() != 0:
                response = "Error executing %s, %d, %s" % (cmd, proc.returncode, errors or output)
            else:
                # Send back the response from sedutils.sedOps
                if errors is not None and \
                   len(errors) > 0:
                    response = "Response: %s\n\nErrors: %s" % (output, errors)
                else:
                    response = "Response: %s" % output
        except Exception as ae:
            logger.warn("PlaneCntrlMsgHandler, _process_msg: %s" % str(ae))
            response = "There was an error processing the request.  Please refer to the logs for details."

        # Transmit the response back as an Ack json msg
        self._send_response(response)

    def ssplCLI_to_sedutilsCLI_converter(self):
        """Convert SSPL's CLI to sedutils CLI
            TODO: Eventually get rid of this and have both CLIs align"""

        self._sedutils_params = ""
        self._sedutils_cmd = "'Not Supported'"

        # Create the parameters that sedutil's CLI understands
        if self._raid_id != "None":
            self._raidset = self._raid_id.split(",")
            self._sedutils_params += " --raidset %s" % self._raid_id

        if self._node_id != "None":
            self._servers = self._node_id.split(",")
            self._sedutils_params += " --server %s" % self._node_id

        if self._drive_id != "None":
            self._drives = self._drive_id.split(",")
            self._sedutils_params += " --drive %s" % self._drive_id

        # Create the sedutil's command to use
        if self._msg_type == "drive":
            if self._plane_request == "list":
               self._sedutils_cmd = "status"

        elif self._msg_type == "config":
            pass

    def _send_response(self, response):
        """Transmit the response back as an Ack json msg"""
        self._log_debug("_send_response, response: %s" % str(response))
        ack_msg = AckResponseMsg("hostname: %s, msg_type: %s, plane_request: %s, drive_id: %s, raid_id: %s" % \
                                 (self._host_name, self._msg_type, self._plane_request, self._drive_id, self._raid_id), \
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
            self._msg_type        = jsonMsg.get("actuator_request_type").get("plane_controller").get("type")
            self._plane_request   = jsonMsg.get("actuator_request_type").get("plane_controller").get("plane_request")
            self._node_id         = jsonMsg.get("actuator_request_type").get("plane_controller").get("parameters").get("node_id")
            self._drive_id        = jsonMsg.get("actuator_request_type").get("plane_controller").get("parameters").get("drive_id")
            self._debug_id        = jsonMsg.get("actuator_request_type").get("plane_controller").get("parameters").get("debug_id")
            self._raid_id         = jsonMsg.get("actuator_request_type").get("plane_controller").get("parameters").get("raid_id")

            # Ignore incorrectly formatted messages
            if self._msg_type is None or \
                self._plane_request is None:
                logger.warn("PlaneCntrlMsgHandler, _parse_jsonMsg, type or plane_request is none")
                return False

            return True
        except Exception as ae:
            logger.warn("PlaneCntrlMsgHandler, _parse_jsonMsg: %s" % str(ae))
            return False


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(PlaneCntrlMsgHandler, self).shutdown()