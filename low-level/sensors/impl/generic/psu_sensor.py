"""
 ****************************************************************************
 Filename:          psu_sensor.py
 Description:       Monitors PSU data using RealStor API.
 Creation Date:     06/24/2019
 Author:            Malhar Vora

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import hashlib
import json
import re

import requests
from zope.interface import implements

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from sensors.Ipsu import IPSUsensor


class RealStorPSUSensor(ScheduledModuleThread, InternalMsgQ):

    implements(IPSUsensor)

    SENSOR_NAME = "RealStorPSUSensor"
    PRIORITY = 1

    STORAGE_ENCLOSURE_KEY = "STORAGE_ENCLOSURE"

    # Keys for connections
    CONTROLLER_IP_KEY = "primary_controller_ip"
    PORT_KEY = "primary_controller_port"

    # Keys for credentials
    CONTROLLER_USERNAME_KEY = "user"
    CONTROLLER_PASSWORD_KEY = "password"

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorPSUSensor.SENSOR_NAME

    def __init__(self):
        super(RealStorPSUSensor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)

        self._controller_ip = None
        self._port = None
        self._api_base_url = None
        self._login_url = None
        self._username = None
        self._password = None
        self._session_key = None

        # Holds PSUs with faults. Used for future reference.
        # TODO: Read this from file
        self._previously_faulty_psus = {}

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorPSUSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorPSUSensor, self).initialize_msgQ(msgQlist)

        # Read configurations
        # Get controller IP to connect to
        self._controller_ip = self._conf_reader._get_value_with_default(
            self.STORAGE_ENCLOSURE_KEY, self.CONTROLLER_IP_KEY, '127.0.0.1')

        # Get port
        self._port = self._conf_reader._get_value_with_default(
            self.STORAGE_ENCLOSURE_KEY, self.PORT_KEY, '80')

        # Get username
        self._username = self._conf_reader._get_value_with_default(
            self.STORAGE_ENCLOSURE_KEY, self.CONTROLLER_USERNAME_KEY, 'manage')

        # Get password
        self._password = self._conf_reader._get_value_with_default(
            self.STORAGE_ENCLOSURE_KEY, self.CONTROLLER_PASSWORD_KEY,
            '!manage')

        self._api_base_url = "http://{0}:{1}/api".format(
            self._controller_ip, self._port)
        self._login_url = "{0}/login".format(self._api_base_url)

        try:
            self._session_key = self._login(self._username, self._password)
        except KeyError as key_error:
            logger.exception("Key not found: {0}".format(key_error))
        except Exception as exception:
            logger.exception(exception)

    def read_data(self):
        """Return the Current PSU information"""
        faulty_psus = self._get_msgs_for_faulty_psus(send_message=False)
        return faulty_psus

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        psus = None
        try:
            psus = self._get_psus(
                {"sessionKey": self._session_key, "dataType": "json"})
            self._get_msgs_for_faulty_psus(psus)
        except Exception as exception:
            logger.exception(exception)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 10 seconds to see if We have a faulty PSU
        self._scheduler.enter(10, self._priority, self.run, ())

    def _get_login_hash(self, username, password):
        credentials = "{0}_{1}".format(username.strip(), password.strip())
        digest = hashlib.sha256(credentials).hexdigest()
        return digest

    def _get_data(self, url, headers=None):
        """Fetches data from API. Returns if HTTP status is 200"""
        response_data = None
        # Send a request
        response = requests.get(url, headers=headers)
        # Convert data only if request is successfull
        if response.status_code == 200:
            # Convert response to JSON
            response_data = json.loads(response.text)
        return response_data

    def _login(self, username, password):
        """Logs in to API and returns a session key"""
        # TODO: Use common login functionality
        session_key = None
        login_hash = self._get_login_hash(username, password)
        login_url_with_hash = "{0}/{1}".format(self._login_url, login_hash)
        login_response = self._get_data(
            login_url_with_hash, {"dataType": "json"})
        session_key = self._extract_session_key(login_response)
        return session_key

    def _extract_session_key(self, response_data):
        """Extracts session key from JSON response"""
        session_key = None
        session_key = response_data["status"][0]["response"]
        return session_key

    def _get_psus(self, headers):
        """Receives list of PSUs from API.
           URL: http://<host>/api/show/power-supplies
        """
        psu_url = "{0}/show/power-supplies".format(self._api_base_url)
        response = self._get_data(psu_url, headers)
        psus = response.get("power-supplies")
        return psus

    def _get_msgs_for_faulty_psus(self, psus, send_message=True):
        """Checks for health of psus and returns list of messages to be
           sent to handler if there are any.
        """
        faulty_psu_messages = []
        internal_json_msg = None
        psu_health = None
        durable_id = None
        alert_type = ""
        for psu in psus:
            psu_health = psu["health"].lower()
            durable_id = psu["durable-id"]
            psu_health_reason = psu["health-reason"]
            if psu_health == "fault":  # Check for missing and fault case
                if durable_id not in self._previously_faulty_psus:
                    alert_type = "fault"
                    # Check for removal
                    if self._check_if_psu_not_installed(psu_health_reason):
                        alert_type = "missing"
                    self._previously_faulty_psus[durable_id] = {
                        "health": psu_health, "alert_type": alert_type}
                    internal_json_msg = self._create_internal_msg(
                        psu, alert_type)
                    faulty_psu_messages.append(internal_json_msg)
                    # Send message to handler
                    if send_message:
                        self._send_json_msg(internal_json_msg)
            elif psu_health == "degraded":  # Check for fault case
                if durable_id not in self._previously_faulty_psus:
                    alert_type = "fault"
                    self._previously_faulty_psus[durable_id] = {
                        "health": psu_health, "alert_type": alert_type}
                    internal_json_msg = self._create_internal_msg(
                        psu, alert_type)
                    faulty_psu_messages.append(internal_json_msg)
                    # Send message to handler
                    if send_message:
                        self._send_json_msg(internal_json_msg)
            elif psu_health == "ok":  # Check for healthy case
                if durable_id in self._previously_faulty_psus:
                    # Send message to handler
                    if send_message:
                        previous_alert_type = \
                            self._previously_faulty_psus[durable_id]["alert_type"]
                        alert_type = "fault_resolved"
                        if previous_alert_type == "missing":
                            alert_type = "insertion"
                        internal_json_msg = self._create_internal_msg(
                            psu, alert_type)
                        faulty_psu_messages.append(internal_json_msg)
                        if send_message:
                            self._send_json_msg(internal_json_msg)
                    del self._previously_faulty_psus[durable_id]
            alert_type = ""
        return faulty_psu_messages

    def _create_internal_msg(self, psu_detail, alert_type):
        """Forms a dictionary containing info about PSUs to send to
           message handler.
        """
        if not psu_detail:
            return {}

        info = {
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
            "status":  psu_detail.get("status")
        }
        extended_info = {
            "durable-id":  psu_detail.get("durable-id"),
            "position":  psu_detail.get("position"),
        }
        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                "enclosure_alert": {
                    "sensor_type": "enclosure_psu_alert",
                    "resource_type": "fru",
                    "alert_type": alert_type,
                    "status": "update"
                },
                "info": info,
                "extended_info": extended_info
            }})
        return internal_json_msg

    def _send_json_msg(self, json_msg):
        """Sends JSON message to Handler"""
        if not json_msg:
            return
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    def _check_if_psu_not_installed(self, health_reason):
        """Checks if PSU is not installed by checking <not installed>
            line in health-reason key. It uses re.findall method to
            check if desired string exists in health-reason. Returns
            boolean based on length of the list of substrings found
            in health-reason. So if length is 0, it returns False,
            else True.
        """
        return bool(re.findall("not installed", health_reason))

    def _load_previously_faulty_psus_from_file(self, filename):
        """
            Loads previous faulty PSU data instance member from file
            if exists.
            TODO: Use this method.
        """
        try:
            data = open(filename).read()
            self._previously_faulty_psus = json.loads(data)
        except:
            logger.warn("File containing previously_faulty_psus not found.")

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorPSUSensor, self).shutdown()
