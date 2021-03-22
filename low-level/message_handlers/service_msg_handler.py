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

import errno
import json
import time
import socket

from framework.actuator_state_manager import actuator_state_manager
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import enabled_products
from json_msgs.messages.actuators.service_controller import ServiceControllerMsg
from json_msgs.messages.sensors.service_watchdog import ServiceWatchdogMsg

from framework.utils.utility import errno_to_str_mapping
from cortx.utils.service import DbusServiceHandler
from framework.utils.conf_utils import (CLUSTER, GLOBAL_CONF, SRVNODE, SSPL_CONF,
                                        Conf, SITE_ID, CLUSTER_ID, NODE_ID,
                                        RACK_ID, STORAGE_SET_ID,
                                        SERVICEMONITOR, MONITORED_SERVICES)
# Modules that receive messages from this module
from message_handlers.logging_msg_handler import LoggingMsgHandler


class ServiceMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for service request messages"""

    MODULE_NAME = "ServiceMsgHandler"
    PRIORITY = 2

    RESOURCE_TYPE = "node:sw:os:service"
    ALERT_TYPE = "UPDATE"
    # Dependency list
    DEPENDENCIES = {
        "plugins": [
            "LoggingMsgHandler",
            "RabbitMQegressProcessor"],
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
        self._dbus_service = DbusServiceHandler()
        # Flag to indicate suspension of module
        self._suspended = False

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(ServiceMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(ServiceMsgHandler, self).initialize_msgQ(msgQlist)

        self._import_products(product)

        self.host_id = socket.getfqdn()
        self.site_id = Conf.get(GLOBAL_CONF,
                                    f'{CLUSTER}>{SRVNODE}>{SITE_ID}','DC01')
        self.rack_id = Conf.get(GLOBAL_CONF,
                                    f'{CLUSTER}>{SRVNODE}>{RACK_ID}','RC01')
        self.node_id = Conf.get(GLOBAL_CONF,
                                    f'{CLUSTER}>{SRVNODE}>{NODE_ID}','SN01')
        self.cluster_id = Conf.get(GLOBAL_CONF, f'{CLUSTER}>{CLUSTER_ID}','CC01')
        self.storage_set_id = Conf.get(GLOBAL_CONF,
                                f'{CLUSTER}>{SRVNODE}>{STORAGE_SET_ID}', 'ST01')
        self.monitored_services = Conf.get(SSPL_CONF,
                                    f'{SERVICEMONITOR}>{MONITORED_SERVICES}')

    def _import_products(self, product):
        """Import classes based on which product is being used"""
        if product.lower() in [x.lower() for x in enabled_products]:
            from zope.component import queryUtility
            self._query_utility = queryUtility

    def run(self):
        """Run the module periodically on its own thread."""
        logger.debug("Start accepting requests")

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
        logger.debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger
        """
        logger.debug(f"_process_msg, jsonMsg: {jsonMsg}")

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        # Parse out the uuid so that it can be sent back in Ack message
        uuid = None
        if jsonMsg.get("sspl_ll_msg_header") is not None and \
           jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            logger.debug(f"_processMsg, uuid: {uuid}")

        # Handle service start, stop, restart, status requests
        if "actuator_request_type" in jsonMsg and \
           "service_controller" in jsonMsg["actuator_request_type"]:

            logger.debug("_processMsg, msg_type: service_controller")

            service_name = jsonMsg.get("actuator_request_type") \
                .get("service_controller").get("service_name")
            service_request = jsonMsg.get("actuator_request_type") \
                .get("service_controller").get("service_request")
            request = f"{service_request}:{service_name}"

            if service_name not in self.monitored_services:
                logger.error(f"{service_name} - service not monitored")
                msg = ("Check if supplied service name is valid, %s is not "
                                        "monitored or managed." % service_name)
                self.send_error_response(service_request, service_name,
                                                            msg, errno.EINVAL)
                return
            elif service_request not in ["disable","enable"]:
                status = self._dbus_service.is_enabled(service_name)
                if status == "disabled":
                    logger.error(f"{service_name} - service is disabled")
                    msg = ("%s is disabled, enable request needed before "
                                "current - %s request can be processed."
                                 % (service_name, service_request ))
                    self.send_error_response(service_request, service_name,
                                                            msg, errno.EPERM)
                    return
            # If the state is INITIALIZED, We can assume that actuator is
            # ready to perform operation.
            if actuator_state_manager.is_initialized("Service"):
                logger.debug(f"_process_msg, service_actuator name: \
                                        {self._service_actuator.name()}")
                self._execute_request(self._service_actuator, jsonMsg, uuid)

            # If the state is INITIALIZING, need to send message
            elif actuator_state_manager.is_initializing("Service"):
                # This state will not be reached. Kept here for consistency.
                logger.info("Service actuator is initializing")
                self.send_error_response(service_request, service_name, \
                        "BUSY - Service actuator is initializing.", errno.EBUSY)

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
                    logger.info(f"_process_msg, service_actuator name: \
                                            {self._service_actuator.name()}")
                    self._execute_request(self._service_actuator, jsonMsg, uuid)
                    actuator_state_manager.set_state("Service",
                                            actuator_state_manager.INITIALIZED)
                else:
                    logger.info("Service actuator is not instantiated")

            # If there is no entry for actuator in table, We can assume
            # that it is not loaded for some reason.
            else:
                logger.warn("Service actuator is not loaded or not supported")

        # Handle events generated by the service monitor
        elif "sensor_request_type" in jsonMsg and \
            "service_status_alert" in jsonMsg["sensor_request_type"]:
            logger.debug(f"Received alert from ServiceMonitor : {jsonMsg}")
            jsonMsg1 = ServiceWatchdogMsg(jsonMsg["sensor_request_type"]).getJson()
            self._write_internal_msgQ("RabbitMQegressProcessor", jsonMsg1)

            # Create an IEM if the resulting service state is failed
            specific_info = \
                jsonMsg['sensor_request_type']['service_status_alert']['specific_info']
            state = specific_info['state']

            if state == "failed":
                internal_json_msg = json.dumps(
                    {"actuator_request_type" : {
                        "logging": {
                            "log_level": "LOG_WARNING",
                            "log_type": "IEM",
                            "log_msg": "IEC: 020003001: Service entered a "\
                                "Failed state : %s"
                                % {json.dumps(specific_info, sort_keys=True)}
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
        service_name = json_msg.get("actuator_request_type").\
                            get("service_controller").get("service_name")
        service_request = json_msg.get("actuator_request_type").\
                            get("service_controller").get("service_request")
        service_info = {}
        service_name, result, error = actuator_instance.\
                                                perform_request(json_msg)
        if error:
            self.send_error_response(service_request, service_name, result)
            return

        logger.debug(f"_processMsg, service_name: {service_name}, \
                                                result: {result}")

        service_info["service_name"] = service_name
        service_info.update(result)

         # Create an actuator response and send it out
        response = self._create_actuator_response(service_info)
        service_controller_msg = ServiceControllerMsg(response)
        if uuid is not None:
            service_controller_msg.set_uuid(uuid)
        json_msg = service_controller_msg.getJson()
        self._write_internal_msgQ("RabbitMQegressProcessor", json_msg)

    def send_error_response(self, request, service_name, err_msg, err_no=None):
        """Send error in response."""
        error_info = {}
        error_response = True
        error_info["service_name"] = service_name
        error_info["request"] = request
        error_info["error_msg"] = err_msg
        if err_no is not None:
            str_err = errno_to_str_mapping(err_no)
            error_info["error_no"] = f"{err_no} - {str_err}"
        response = self._create_actuator_response(error_info, error_response)
        service_controller_msg = ServiceControllerMsg(response).getJson()
        self._write_internal_msgQ("RabbitMQegressProcessor",
                                                    service_controller_msg)

    def _create_actuator_response(self, service_info, is_error=False):
        """Create JSON msg."""
        if is_error:
            severity = "warning"
        else:
            severity = "informational"
        resource_id = service_info.get("service_name")
        epoch_time = str(int(time.time()))
        specific_info = []
        info = {
            "cluster_id": self.cluster_id,
            "site_id": self.site_id,
            "rack_id": self.rack_id,
            "storage_set_id": self.storage_set_id,
            "node_id": self.node_id,
            "resource_id": resource_id,
            "resource_type": self.RESOURCE_TYPE,
            "event_time": epoch_time
          }

        specific_info.append(service_info)

        response = {
          "alert_type": self.ALERT_TYPE,
          "severity": severity,
          "host_id": self.host_id,
          "instance_id": resource_id,
          "info": info,
          "specific_info": specific_info
        }

        return response

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
