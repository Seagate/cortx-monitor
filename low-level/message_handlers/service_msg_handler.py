"""
 ****************************************************************************
 Filename:          service__msg_handler.py
 Description:       Message Handler for service request messages
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

import errno
import json

from framework.actuator_state_manager import actuator_state_manager
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import enabled_products
from json_msgs.messages.actuators.service_controller import ServiceControllerMsg
from json_msgs.messages.sensors.service_watchdog import ServiceWatchdogMsg
from json_msgs.messages.actuators.ack_response import AckResponseMsg
# Modules that receive messages from this module
from message_handlers.logging_msg_handler import LoggingMsgHandler


class ServiceMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for service request messages"""

    MODULE_NAME = "ServiceMsgHandler"
    PRIORITY = 2

    # Dependency list
    DEPENDENCIES = {
        "plugins": [
            "LoggingMsgHandler",
            "EgressProcessor"],
        "rpms": []
    }

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return ServiceMsgHandler.DEPENDENCIES

    @staticmethod
    def name():
        """ @return: name of the module."""
        return ServiceMsgHandler.MODULE_NAME

    def __init__(self):
        super(ServiceMsgHandler, self).__init__(self.MODULE_NAME,
                                                self.PRIORITY)
        self._service_actuator = None
        self._query_utility = None

        # Flag to indicate suspension of module
        self._suspended = False

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(ServiceMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(ServiceMsgHandler, self).initialize_msgQ(msgQlist)

        self._import_products(product)

    def _import_products(self, product):
        """Import classes based on which product is being used"""
        if product.lower() in [x.lower() for x in enabled_products]:
            from zope.component import queryUtility
            self._query_utility = queryUtility

    def run(self):
        """Run the module periodically on its own thread."""
        self._log_debug("Start accepting requests")

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(1, self._priority, self.run, ())
            return

        # self._set_debug(True)
        # self._set_debug_persist(True)

        try:
            # Block on message queue until it contains an entry
            json_msg, _ = self._read_my_msgQ()
            if json_msg is not None:
                self._process_msg(json_msg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                json_msg, _ = self._read_my_msgQ()
                if json_msg is not None:
                    self._process_msg(json_msg)

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception(f"ServiceMsgHandler restarting: {ae}")

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger
        """
        self._log_debug(f"_process_msg, jsonMsg: {jsonMsg}")

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        # Parse out the uuid so that it can be sent back in Ack message
        uuid = None
        if jsonMsg.get("sspl_ll_msg_header") is not None and \
           jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            self._log_debug(f"_processMsg, uuid: {uuid}")

        # Handle service start, stop, restart, status requests
        if jsonMsg.get("actuator_request_type").get("service_controller") is not None:
            self._log_debug("_processMsg, msg_type: service_controller")

            service_name = jsonMsg.get("actuator_request_type") \
                .get("service_controller").get("service_name")
            service_request = jsonMsg.get("actuator_request_type") \
                .get("service_controller").get("service_request")
            request = f"{service_request}:{service_name}"

            # If the state is INITIALIZED, We can assume that actuator is
            # ready to perform operation.
            if actuator_state_manager.is_initialized("Service"):
                self._log_debug(f"_process_msg, service_actuator name: {self._service_actuator.name()}")
                self._execute_request(self._service_actuator, jsonMsg, uuid)

            # If the state is INITIALIZING, need to send message
            elif actuator_state_manager.is_initializing("Service"):
                # This state will not be reached. Kept here for consistency.
                logger.info("Service actuator is initializing")
                busy_json_msg = AckResponseMsg(
                    request, "BUSY", uuid, error_no=errno.EBUSY).getJson()
                self._write_internal_msgQ(
                    "EgressProcessor", busy_json_msg)

            elif actuator_state_manager.is_imported("Service"):
                # This case will be for first request only. Subsequent
                # requests will go to INITIALIZED state case.
                logger.info("Service actuator is imported and initializing")
                from actuators.IService import IService
                actuator_state_manager.set_state(
                    "Service", actuator_state_manager.INITIALIZING)
                service_actuator_class = self._query_utility(IService)
                if service_actuator_class:
                    # NOTE: Instantiation part should not time consuming
                    # otherwise ServiceMsgHandler will get block and will
                    # not be able serve any subsequent requests. This applies
                    # to instantiation of evey actuator.
                    self._service_actuator = service_actuator_class()
                    logger.info(f"_process_msg, service_actuator name: {self._service_actuator.name()}")
                    self._execute_request(
                        self._service_actuator, jsonMsg, uuid)
                    actuator_state_manager.set_state(
                        "Service", actuator_state_manager.INITIALIZED)
                else:
                    logger.info("Service actuator is not instantiated")

            # If there is no entry for actuator in table, We can assume
            # that it is not loaded for some reason.
            else:
                logger.warn("Service actuator is not loaded or not supported")

        # Handle events generated by the service watchdogs
        elif jsonMsg.get("actuator_request_type").get("service_watchdog_controller") is not None:
            self._log_debug("_processMsg, msg_type: service_watchdog_controller")

            # Parse out values to be sent
            service_name = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("service_name")
            state = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("state")
            prev_state = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("previous_state")
            substate = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("substate")
            prev_substate = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("previous_substate")
            pid = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("pid")
            prev_pid = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("previous_pid")

            # Pull out the service_request and if it's equal to "status" then get current status (state, substate)
            service_request = jsonMsg.get("actuator_request_type").get("service_watchdog_controller").get("service_request")
            if service_request != "None":
                # Query the Zope GlobalSiteManager for an object implementing IService
                if self._service_actuator is None:
                    from actuators.IService import IService
                    self._service_actuator = self._query_utility(IService)()
                    self._log_debug(f"_process_msg, service_actuator name: {self._service_actuator.name()}")
                service_name, state, substate = self._service_actuator.perform_request(jsonMsg)

                self._log_debug(f"_processMsg, service_name: {service_name}, state: {state}, substate: {substate}")
                self._log_debug(f"_processMsg, prev state: {prev_state}, prev substate: {prev_substate}")

            # Create a service watchdog message and send it out
            jsonMsg = ServiceWatchdogMsg(service_name, state, prev_state, substate, prev_substate, pid, prev_pid).getJson()
            self._write_internal_msgQ("EgressProcessor", jsonMsg)

            # Create an IEM if the resulting service state is failed
            if "fail" in state.lower() or \
                "fail" in substate.lower():
                json_data = {"service_name": service_name,
                             "state": state,
                             "previous_state": prev_state,
                             "substate": substate,
                             "previous_substate": prev_substate,
                             "pid": pid,
                             "previous_pid": prev_pid
                            }

                internal_json_msg = json.dumps(
                    {"actuator_request_type" : {
                        "logging": {
                            "log_level": "LOG_WARNING",
                            "log_type": "IEM",
                            "log_msg": f"IEC: 020003001: Service entered a Failed state : {json.dumps(json_data, sort_keys=True)}"
                            }
                        }
                    })

                # Send the event to logging msg handler to send IEM message to journald
                self._write_internal_msgQ(
                    LoggingMsgHandler.name(), internal_json_msg)

        # ... handle other service message types

    def _execute_request(self, actuator_instance, json_msg, uuid):
        """Calls perform_request method of an actuator and sends response to
           output channel.
        """
        service_name, state, substate = \
            actuator_instance.perform_request(json_msg)

        if substate:
            result = f"{state}:{substate}"
        else:
            result = state

        self._log_debug(f"_processMsg, service_name: {service_name}, result: {result}")

        # Create an actuator response and send it out
        service_controller_msg = ServiceControllerMsg(service_name, result)
        if uuid is not None:
            service_controller_msg.set_uuid(uuid)
        json_msg = service_controller_msg.getJson()
        self._write_internal_msgQ("EgressProcessor", json_msg)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(ServiceMsgHandler, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(ServiceMsgHandler, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(ServiceMsgHandler, self).shutdown()
