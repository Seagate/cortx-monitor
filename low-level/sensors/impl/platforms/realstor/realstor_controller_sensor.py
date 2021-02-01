# Copyright (c) 2019-2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Monitors Controller data using RealStor API.
 ****************************************************************************
"""
import json
import os
import socket
import time
import uuid
from threading import Event

from zope.interface import implementer

from cortx.sspl.framework.base.internal_msgQ import InternalMsgQ
from cortx.sspl.framework.base.module_thread import SensorThread
from cortx.sspl.framework.platforms.realstor.realstor_enclosure import \
    singleton_realstorencl
from cortx.sspl.framework.utils.conf_utils import (POLLING_FREQUENCY_OVERRIDE,
    SSPL_CONF, Conf)
from cortx.sspl.framework.utils.service_logging import logger
from cortx.sspl.framework.utils.severity_reader import SeverityReader
from cortx.sspl.framework.utils.store_factory import store
# Modules that receive messages from this module
from cortx.sspl.message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from cortx.sspl.sensors.Icontroller import IControllersensor


@implementer(IControllersensor)
class RealStorControllerSensor(SensorThread, InternalMsgQ):
    """Monitors Controller data using RealStor API"""


    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RealStorEnclMsgHandler"],
                    "rpms": []
    }

    SENSOR_NAME = "RealStorControllerSensor"
    SENSOR_RESP_TYPE = "enclosure_controller_alert"
    RESOURCE_CATEGORY = "fru"
    RESOURCE_TYPE = "enclosure:fru:controller"

    PRIORITY          = 1

    # Controllers directory name
    CONTROLLERS_DIR = "controllers"

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorControllerSensor.SENSOR_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return RealStorControllerSensor.DEPENDENCIES

    def __init__(self):
        super(RealStorControllerSensor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)

        self._faulty_controller_file_path = None

        self.rssencl = singleton_realstorencl

        # controllers persistent cache
        self._controller_prcache = None

        # Holds Controllers with faults. Used for future reference.
        self._previously_faulty_controllers = {}

        self.pollfreq_controllersensor = \
            int(Conf.get(SSPL_CONF,f"{self.rssencl.CONF_REALSTORCONTROLLERSENSOR}>{POLLING_FREQUENCY_OVERRIDE}",
                                0))

        if self.pollfreq_controllersensor == 0:
                self.pollfreq_controllersensor = self.rssencl.pollfreq

        # Flag to indicate suspension of module
        self._suspended = False

        self._event = Event()

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorControllerSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorControllerSensor, self).initialize_msgQ(msgQlist)

        self._controller_prcache = os.path.join(self.rssencl.frus,\
             self.CONTROLLERS_DIR)

        # Persistence file location. This file stores faulty Controller data
        self._faulty_controller_file_path = os.path.join(
            self._controller_prcache, "controllerdata.json")

        # Load faulty Controller data from file if available
        self._previously_faulty_controllers = store.get(\
                                                  self._faulty_controller_file_path)

        if self._previously_faulty_controllers is None:
            self._previously_faulty_controllers = {}
            store.put(self._previously_faulty_controllers,\
                self._faulty_controller_file_path)

        return True

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(10, self._priority, self.run, ())
            return

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        controllers = None
        try:
            controllers = self._get_controllers()

            if controllers:
                self._get_msgs_for_faulty_controllers(controllers)

        except Exception as exception:
            logger.exception(exception)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 10 seconds to see if We have a faulty Controller
        self._scheduler.enter(self.pollfreq_controllersensor,
                self._priority, self.run, ())

    def _get_controllers(self):
        """Receives list of Controllers from API.
           URL: http://<host>/api/show/controllers
        """
        url = self.rssencl.build_url(self.rssencl.URI_CLIAPI_SHOWCONTROLLERS)

        response = self.rssencl.ws_request(url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn(f"{self.rssencl.LDR_R1_ENCL}:: Controllers status unavailable as ws request {url}")
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(f"{self.rssencl.LDR_R1_ENCL}:: http request {url} to get controllers failed with \
                     err {response.status_code}")
            return

        response_data = json.loads(response.text)
        controllers = response_data.get("controllers")
        return controllers

    def _get_msgs_for_faulty_controllers(self, controllers, send_message=True):
        """Checks for health of controllers and returns list of messages to be
           sent to handler if there are any.
        """
        faulty_controller_messages = []
        internal_json_msg = None
        controller_health = None
        durable_id = None
        alert_type = ""
        # Flag to indicate if there is a change in _previously_faulty_controllers
        state_changed = False
        prev_alert_type = None

        if not controllers:
            return
        for controller in controllers:
            controller_health = controller["health"].lower()
            controller_status = controller["status"].lower()
            durable_id = controller["durable-id"]

            # Check for missing and fault case
            if controller_health == self.rssencl.HEALTH_FAULT:
                # Status change from Degraded ==> Fault or OK ==> Fault
                if (durable_id in self._previously_faulty_controllers and \
                        self._previously_faulty_controllers[durable_id]['health']=="degraded") or \
                        (durable_id not in self._previously_faulty_controllers):
                    alert_type = self.rssencl.FRU_FAULT
                    # Check for removal
                    if controller_status == self.rssencl.STATUS_NOTINSTALLED:
                        alert_type = self.rssencl.FRU_MISSING
                    self._previously_faulty_controllers[durable_id] = {
                        "health": controller_health, "alert_type": alert_type}
                    state_changed = True
                    internal_json_msg = self._create_internal_msg(
                        controller, alert_type)
                    faulty_controller_messages.append(internal_json_msg)
                    # Send message to handler
                    if send_message:
                        self._send_json_msg(internal_json_msg)
            # Check for fault case
            elif controller_health == self.rssencl.HEALTH_DEGRADED:
                # Status change from Fault ==> Degraded or OK ==> Degraded
                # Controller can also go into degraded state after installation as well
                # So, Degrade state can be after missing alert as well.
                if (durable_id in self._previously_faulty_controllers and \
                        self._previously_faulty_controllers[durable_id]['health']=="fault") or \
                        (durable_id not in self._previously_faulty_controllers):
                    if self._previously_faulty_controllers and \
                            self._previously_faulty_controllers.get(durable_id).get('alert_type'):
                        prev_alert_type = self._previously_faulty_controllers[durable_id]["alert_type"]

                    # If prev_alert_type is missing, then the next alert type will be insertion first
                    if prev_alert_type and prev_alert_type.lower() == self.rssencl.FRU_MISSING:
                        alert_type = self.rssencl.FRU_INSERTION

                        internal_json_msg = self._create_internal_msg(
                                    controller, alert_type)

                        # send the message to the handler
                        if send_message:
                            self._send_json_msg(internal_json_msg)

                    # And set alert_type as fault
                    alert_type = self.rssencl.FRU_FAULT
                    self._previously_faulty_controllers[durable_id] = {
                        "health": controller_health, "alert_type": alert_type}

                    internal_json_msg = self._create_internal_msg(controller, alert_type)
                    faulty_controller_messages.append(internal_json_msg)

                    state_changed = True

                    # send the message to the handler
                    if send_message:
                        self._send_json_msg(internal_json_msg)

            # Check for healthy case
            elif controller_health == self.rssencl.HEALTH_OK:
                # Status change from Fault ==> OK or Degraded ==> OK
                if durable_id in self._previously_faulty_controllers:
                    # Send message to handler
                    if send_message:
                        previous_alert_type = \
                            self._previously_faulty_controllers[durable_id]["alert_type"]
                        alert_type = self.rssencl.FRU_FAULT_RESOLVED
                        if previous_alert_type == self.rssencl.FRU_MISSING:
                            alert_type = self.rssencl.FRU_INSERTION
                        internal_json_msg = self._create_internal_msg(
                            controller, alert_type)
                        faulty_controller_messages.append(internal_json_msg)
                        if send_message:
                            self._send_json_msg(internal_json_msg)
                    del self._previously_faulty_controllers[durable_id]
                    state_changed = True
            # Persist faulty Controller list to file only if something is changed
            if state_changed:
                # Wait till msg is sent to rabbitmq or added in consul for resending.
                # If timed out, do not update cache and revert in-memory cache.
                # So, in next iteration change can be detected
                if self._event.wait(self.rssencl.PERSISTENT_DATA_UPDATE_TIMEOUT):
                    store.put(self._previously_faulty_controllers,\
                        self._faulty_controller_file_path)
                else:
                    self._previously_faulty_controllers = store.get(self._faulty_controller_file_path)
                state_changed = False
            alert_type = ""
        return faulty_controller_messages

    def _create_internal_msg(self, controller_detail, alert_type):
        """Forms a dictionary containing info about Controllers to send to
           message handler.
        """
        if not controller_detail:
            return {}

        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        resource_id = controller_detail.get("durable-id", "")
        host_name = socket.gethostname()
        info = {
                "site_id": self.rssencl.site_id,
                "cluster_id": self.rssencl.cluster_id,
                "rack_id": self.rssencl.rack_id,
                "node_id": self.rssencl.node_id,
                "resource_type": self.RESOURCE_TYPE,
                "resource_id": resource_id,
                "event_time": epoch_time
                }

        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                "enclosure_alert": {
                    "host_id": host_name,
                    "severity": severity,
                    "alert_id": alert_id,
                    "alert_type": alert_type,
                    "status": "update",
                    "info": info,
                    "specific_info": controller_detail
                }
            }})

        return internal_json_msg

    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
           epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

    def _send_json_msg(self, json_msg):
        """Sends JSON message to Handler"""
        if not json_msg:
            return
        self._event.clear()
        # RAAL stands for - RAise ALert
        logger.info(f"RAAL: {json_msg}")
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg, self._event)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RealStorControllerSensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RealStorControllerSensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorControllerSensor, self).shutdown()
