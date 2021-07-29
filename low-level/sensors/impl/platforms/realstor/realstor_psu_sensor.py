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
  Description:       Monitors PSU using RealStor API.
 ****************************************************************************
"""
import json
import os
import re
import time
import uuid
from threading import Event

from zope.interface import implementer

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from framework.platforms.realstor.realstor_enclosure import \
    singleton_realstorencl
from framework.utils.conf_utils import (POLLING_FREQUENCY_OVERRIDE, SSPL_CONF,
                                        Conf)
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from framework.utils.store_factory import store
from framework.utils.os_utils import OSUtils
# Modules that receive messages from this module
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from sensors.Ipsu import IPSUsensor


@implementer(IPSUsensor)
class RealStorPSUSensor(SensorThread, InternalMsgQ):
    """Monitors PSU data using RealStor API"""


    SENSOR_NAME = "RealStorPSUSensor"
    RESOURCE_CATEGORY = "enclosure:hw:psu"

    PRIORITY = 1

    # PSUs directory name
    PSUS_DIR = "psus"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RealStorEnclMsgHandler"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorPSUSensor.SENSOR_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return RealStorPSUSensor.DEPENDENCIES

    def __init__(self):
        super(RealStorPSUSensor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)

        self._faulty_psu_file_path = None

        self.rssencl = singleton_realstorencl

        # psus persistent cache
        self.psu_prcache = None

        # Holds PSUs with faults. Used for future reference.
        self._previously_faulty_psus = {}

        self.pollfreq_psusensor = \
            int(Conf.get(SSPL_CONF, f"{self.rssencl.CONF_REALSTORPSUSENSOR}>{POLLING_FREQUENCY_OVERRIDE}",
                        0))

        if self.pollfreq_psusensor == 0:
                self.pollfreq_psusensor = self.rssencl.pollfreq

        # Flag to indicate suspension of module
        self._suspended = False

        self._event = Event()
        self.os_utils = OSUtils()

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorPSUSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorPSUSensor, self).initialize_msgQ(msgQlist)

        self.psu_prcache = os.path.join(self.rssencl.frus, self.PSUS_DIR)

        # Persistence file location. This file stores faulty PSU data
        self._faulty_psu_file_path = os.path.join(
            self.psu_prcache, "psudata.json")
        self._log_debug(
            f"_faulty_psu_file_path: {self._faulty_psu_file_path}")

        # Load faulty PSU data from file if available
        self._previously_faulty_psus = store.get(\
                                           self._faulty_psu_file_path)

        if self._previously_faulty_psus is None:
            self._previously_faulty_psus = {}
            store.put(self._previously_faulty_psus,\
                self._faulty_psu_file_path)

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

        psus = None

        psus = self._get_psus()

        if psus:
            self._get_msgs_for_faulty_psus(psus)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 10 seconds to see if We have a faulty PSU
        self._scheduler.enter(self.pollfreq_psusensor,
                self._priority, self.run, ())

    def _get_psus(self):
        """Receives list of PSUs from API.
           URL: http://<host>/api/show/power-supplies
        """
        url = self.rssencl.build_url(
                  self.rssencl.URI_CLIAPI_SHOWPSUS)

        response = self.rssencl.ws_request(
                        url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn(f"{self.rssencl.LDR_R1_ENCL}:: PSUs status unavailable as ws request {url} failed")
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(f"{self.rssencl.LDR_R1_ENCL}:: http request {url} to get power-supplies failed   \
                                       with err {response.status_code}")
            return

        response_data = json.loads(response.text)
        psus = response_data.get("power-supplies")
        return psus

    def _get_msgs_for_faulty_psus(self, psus, send_message = True):
        """Checks for health of psus and returns list of messages to be
           sent to handler if there are any.
        """
        self._log_debug(
            f"RealStorPSUSensor._get_msgs_for_faulty_psus -> {psus} {send_message}")
        faulty_psu_messages = []
        internal_json_msg = None
        psu_health = None
        durable_id = None
        alert_type = ""
        # Flag to indicate if there is a change in _previously_faulty_psus
        state_changed = False

        if not psus:
            return
        for psu in psus:
            psu_health = psu["health"].lower()
            durable_id = psu["durable-id"]
            psu_health_reason = psu["health-reason"]
            # Check for missing and fault case
            if psu_health == self.rssencl.HEALTH_FAULT:
                self._log_debug("Found fault in PSU {0}".format(durable_id))
                alert_type = self.rssencl.FRU_FAULT
                # Check for removal
                if self._check_if_psu_not_installed(psu_health_reason):
                    alert_type = self.rssencl.FRU_MISSING
                state_changed = not (durable_id in self._previously_faulty_psus and
                        self._previously_faulty_psus[durable_id]["alert_type"] == alert_type)
                if state_changed:
                    self._previously_faulty_psus[durable_id] = {
                        "health": psu_health, "alert_type": alert_type}
                    internal_json_msg = self._create_internal_msg(
                        psu, alert_type)
                    faulty_psu_messages.append(internal_json_msg)
                    # Send message to handler
                    if send_message:
                        self._send_json_msg(internal_json_msg)
            # Check for fault case
            elif psu_health == self.rssencl.HEALTH_DEGRADED:
                self._log_debug("Found degraded in PSU {0}".format(durable_id))
                state_changed = durable_id not in self._previously_faulty_psus
                if state_changed:
                    alert_type = self.rssencl.FRU_FAULT
                    self._previously_faulty_psus[durable_id] = {
                        "health": psu_health, "alert_type": alert_type}
                    internal_json_msg = self._create_internal_msg(
                        psu, alert_type)
                    faulty_psu_messages.append(internal_json_msg)
                    # Send message to handler
                    if send_message:
                        self._send_json_msg(internal_json_msg)
            # Check for healthy case
            elif psu_health == self.rssencl.HEALTH_OK:
                self._log_debug("Found ok in PSU {0}".format(durable_id))
                state_changed = durable_id in self._previously_faulty_psus
                if state_changed:
                    # Send message to handler
                    if send_message:
                        previous_alert_type = \
                            self._previously_faulty_psus[durable_id]["alert_type"]
                        alert_type = self.rssencl.FRU_FAULT_RESOLVED
                        if previous_alert_type == self.rssencl.FRU_MISSING:
                            alert_type = self.rssencl.FRU_INSERTION
                        internal_json_msg = self._create_internal_msg(
                            psu, alert_type)
                        faulty_psu_messages.append(internal_json_msg)
                        if send_message:
                            self._send_json_msg(internal_json_msg)
                    del self._previously_faulty_psus[durable_id]
            # Persist faulty PSU list to file only if something is changed
            if state_changed:
                # Wait till msg is sent to message bus or added in consul for resending.
                # If timed out, do not update cache and revert in-memory cache.
                # So, in next iteration change can be detected
                if self._event.wait(self.rssencl.PERSISTENT_DATA_UPDATE_TIMEOUT):
                    store.put(self._previously_faulty_psus,\
                        self._faulty_psu_file_path)
                else:
                    self._previously_faulty_psus = store.get(self._faulty_psu_file_path)
                state_changed = False
            alert_type = ""
        return faulty_psu_messages

    def _get_hostname(self):
        try:
            return self.os_utils.get_fqdn()
        except Exception as e:
            logger.exception("Got exception {} when trying to get hostname"
                    " using getfqdn().".format(e))

        logger.info(" Trying with ip addr command")
        try:
            from subprocess import run, PIPE
            from re import findall

            IP_CMD = "ip -f inet addr show scope global up | grep inet"
            IP_REGEX = b'\\b(\\d{1,3}(?:\\.\d{1,3}){3})/\d{1,2}\\b'

            ip_out = run(IP_CMD, stdout=PIPE, shell=True, check=True)
            ip_list = re.findall(IP_REGEX, ip_out.stdout)
            if ip_list:
                return ip_list[0]
        except Exception as e:
            logger.exception("Got exception {} when trying to get hostname"
                    " using ip addr command.".format(e))

        # Ultimate fallback, when we are completely out of options
        logger.info("Using localhost")
        return "localhost"

    def _create_internal_msg(self, psu_detail, alert_type):
        """Forms a dictionary containing info about PSUs to send to
           message handler.
        """
        self._log_debug(
            f"RealStorPSUSensor._create_internal_msg -> {psu_detail} {alert_type}")
        if not psu_detail:
            return {}

        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        fru = self.rssencl.is_storage_fru('POWER_SUPPLY')
        resource_id = psu_detail.get("durable-id")
        host_name = self._get_hostname()

        info = {
                "resource_type": self.RESOURCE_CATEGORY,
                "fru": fru,
                "resource_id": resource_id,
                "event_time": epoch_time
                }

        specific_info = {
            "enclosure-id": psu_detail.get("enclosure-id"),
            "serial-number":  psu_detail.get("serial-number"),
            "description":  psu_detail.get("description"),
            "revision":  psu_detail.get("revision"),
            "model":  psu_detail.get("model"),
            "vendor":  psu_detail.get("vendor"),
            "location":  psu_detail.get("location"),
            "part-number":  psu_detail.get("part-number"),
            "fru-shortname":  psu_detail.get("fru-shortname"),
            "mfg-date":  psu_detail.get("mfg-date"),
            "mfg-vendor-id":  psu_detail.get("mfg-vendor-id"),
            "dc12v":  psu_detail.get("dc12v"),
            "dc5v":  psu_detail.get("dc12v"),
            "dc33v":  psu_detail.get("dc33v"),
            "dc12i":  psu_detail.get("dc12i"),
            "dc5i":  psu_detail.get("dc5i"),
            "dctemp":  psu_detail.get("dctemp"),
            "health":  psu_detail.get("health"),
            "health-reason":  psu_detail.get("health-reason"),
            "health-recommendation":  psu_detail.get("health-recommendation"),
            "status":  psu_detail.get("status"),
            "durable-id":  psu_detail.get("durable-id"),
            "position":  psu_detail.get("position"),
        }

        for k in specific_info.keys():
            if specific_info[k] == "":
                specific_info[k] = "N/A"

        # Creates internal json message request structure.
        # this message will be passed to the StorageEnclHandler
        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                "enclosure_alert": {
                        "status": "update",
                        "host_id": host_name,
                        "alert_type": alert_type,
                        "severity": severity,
                        "alert_id": alert_id,
                        "info": info,
                        "specific_info": specific_info
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
        self._log_debug(
            "RealStorPSUSensor._send_json_msg -> {0}".format(json_msg))
        if not json_msg:
            return
        self._event.clear()
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg, self._event)

    def _check_if_psu_not_installed(self, health_reason):
        """Checks if PSU is not installed by checking <not installed>
            line in health-reason key. It uses re.findall method to
            check if desired string exists in health-reason. Returns
            boolean based on length of the list of substrings found
            in health-reason. So if length is 0, it returns False,
            else True.
        """
        return bool(re.findall("not installed", health_reason))

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RealStorPSUSensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RealStorPSUSensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorPSUSensor, self).shutdown()
