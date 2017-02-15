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
import os
import json
import syslog
import logging

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from framework.rabbitmq.plane_cntrl_rmq_egress_processor import PlaneCntrlRMQegressProcessor
from json_msgs.messages.actuators.ack_response import AckResponseMsg

# Need to track down an RPM for python-prct as RE won't go for easy-install, pip, setup.py, etc
try:
    import prctl

    from seddispatch import SedOpDispatch
    from pwd import getpwnam
    from grp import getgrnam
except ImportError as ie:
    logger.info("If using Plane Controller Message handler then please install python-prctl package.")


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

        # Remove root privileges to control possible access
        self._dropPrivileges("sspl-ll")

    def run(self):
        """Run the module on its own thread blocking for incoming messages."""
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
        """Parses the incoming message and process"""
        if isinstance(jsonMsg, dict) == False:
            jsonMsg = json.loads(jsonMsg)

        # Parse json msg into usable fields
        success = self._parse_jsonMsg(jsonMsg)
        if not success:
            response = "An error occurred parsing JSON fields"
            self._send_response(response)
            return

        try:
            sedOpDispatch = SedOpDispatch(self._command, self._parameters, self._arguments)
            status = sedOpDispatch.status

            # Don't continue on init errors, invalid command or doesn't apply to this node
            if sedOpDispatch.status != 0:
                errors = sedOpDispatch.errors
                self._log_debug("_process_msg, status: %s, errors: %s" % \
                                (str(sedOpDispatch.status), str(errors)))
                return

            status   = sedOpDispatch.run()
            response = sedOpDispatch.output
            errors   = sedOpDispatch.errors            
            hostname = sedOpDispatch.hostname

            # Transmit the response back as an Ack json msg
            self._send_response(response, errors, status, hostname)

            self._log_debug("PlaneCntrlMsgHandler, _process_msg, status: %s, command: %s, parameters: %s, args: %s" % \
                        (str(status), str(self._command), str(self._parameters), str(self._arguments)))
            self._log_debug("PlaneCntrlMsgHandler, _process_msg, response: %s" % str(response))
            self._log_debug("PlaneCntrlMsgHandler, _process_msg, errors: %s" % str(errors))
        except Exception as ae:
            logger.warn("PlaneCntrlMsgHandler, _process_msg: %s" % str(ae))
            response = "There was an error processing the request.  Please refer to the logs for details."

    def _send_response(self, response, errors, status, hostname):
        """Transmit the response back as an Ack json msg"""
        self._log_debug("_send_response, response: %s" % str(response))
        ack_msg = AckResponseMsg("hostname: %s, command: %s, parameters: %s, arguments: %s, status: %s, errors: %s" % \
                                 (hostname, str(self._command), str(self._parameters), str(self._arguments), \
                                  str(status), str(errors)), \
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
                self._log_debug("_processMsg, uuid: %s" % self._uuid)

            # Parse out values from msg
            self._command    = jsonMsg.get("actuator_request_type").get("plane_controller").get("command")
            self._parameters = jsonMsg.get("actuator_request_type").get("plane_controller").get("parameters")
            self._arguments  = jsonMsg.get("actuator_request_type").get("plane_controller").get("arguments")

            # Ignore incorrectly formatted messages
            if self._command is None:
                logger.warn("PlaneCntrlMsgHandler, _parse_jsonMsg, command is none")
                logger.warn("PlaneCntrlMsgHandler, _process_msg, command: %s" % str(self._command))
                return False

            return True
        except Exception as ae:
            logger.warn("PlaneCntrlMsgHandler, _parse_jsonMsg: %s" % str(ae))
            return False

    def _dropPrivileges(self, user):
        """Remove root privileges to control possible access"""
        altgroups = ('disk',)
        transition_caps = ('setuid', 'setgid')
        keep_caps = ('sys_rawio',)

        prctl.securebits.no_setuid_fixup = True

        prctl.cap_effective.limit(*transition_caps + keep_caps)
        prctl.cap_permitted.limit(*transition_caps + keep_caps)

        pw = getpwnam(user)
        os.setgid(pw.pw_gid)
        os.setuid(pw.pw_uid)

        os.setgroups([getgrnam(gname).gr_gid for gname in altgroups])

        prctl.cap_effective.drop(*transition_caps)
        prctl.cap_permitted.drop(*transition_caps)


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(PlaneCntrlMsgHandler, self).shutdown()
