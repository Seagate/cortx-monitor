"""
 ****************************************************************************
 Filename:          relstor_sideplane_expander_sensor.py
 Description:       Monitors Sideplane Expander data using RealStor API
 Creation Date:     07/22/2019
 Author:            Madhura Mande

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

import requests
from zope.interface import implements

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from message_handlers.logging_msg_handler import LoggingMsgHandler
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from sensors.ISideplane_expander import ISideplaneExpandersensor


class RealStorSideplaneExpanderSensor(ScheduledModuleThread, InternalMsgQ):

    implements(ISideplaneExpandersensor)

    SENSOR_NAME = "RealStorSideplaneExpanderSensor"
    PRIORITY = 1

    LOGIN_HEADERS = {"dataType": "json"}

    # sspl configuration keys
    REALSTORENCLOSURE_KEY = "STORAGE_ENCLOSURE"
    CONTROLLER_IP_KEY = "primary_controller_ip"
    CONTROLLER_PORT_KEY = "primary_controller_port"
    CONTROLLER_USERNAME_KEY = "user"
    CONTROLLER_PASSWORD_KEY = "password"

    RESOURCE_TYPE = "fru"
    SENSOR_TYPE = "enclosure_sideplane_expander_alert"

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorSideplaneExpanderSensor.SENSOR_NAME

    def __init__(self):
        super(RealStorSideplaneExpanderSensor, self).__init__(self.SENSOR_NAME,
                                         self.PRIORITY)

        self._controller_ip = None
        self._port = None
        self._username = None
        self._password = None
        self._api_base_url = None
        self._api_login_url = None
        self._session_key = None
        self._faulty_sideplane_expander_list = []
        self._faulty_sideplane_expander_dict = {}

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorSideplaneExpanderSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorSideplaneExpanderSensor, self).initialize_msgQ(msgQlist)

        # Read configuration file
        # Read Controller IP
        self._controller_ip = self._conf_reader._get_value_with_default(
            self.REALSTORENCLOSURE_KEY, self.CONTROLLER_IP_KEY, '127.0.0.1')

        # Read Controller Port
        self._controller_port = self._conf_reader._get_value_with_default(
            self.REALSTORENCLOSURE_KEY, self.CONTROLLER_PORT_KEY, '80')

        # Read Username
        self._username = self._conf_reader._get_value_with_default(
            self.REALSTORENCLOSURE_KEY, self.CONTROLLER_USERNAME_KEY, 'manage')

        # Read password
        self._password = self._conf_reader._get_value_with_default(
            self.REALSTORENCLOSURE_KEY, self.CONTROLLER_PASSWORD_KEY, '!manage')

        self._api_base_url = "http://{0}:{1}/api".format(self._controller_ip,
            self._controller_port)
        self._api_login_url = "{0}/login".format(self._api_base_url)

        try:
            self._session_key = self._do_login()
        except KeyError as key_error:
            logger.exception("Unable to get session Key: {0}".format(key_error))
        except Exception as exception:
            logger.exception(exception)

    def read_data(self):
        """Return the Current RAID status information"""
        return self._sideplane_expander_list

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        # periodically check are there any faults found in sideplane expanders
        self._check_for_sideplane_expander_fault()

        self._scheduler.enter(30, self._priority, self.run, ())

    def _do_login(self):
        """Logs in into the system through API and returns session key"""

        session_key = None
        hash_val = self._get_hash(self._username, self._password)
        login_url = "{0}/{1}".format(self._api_login_url, hash_val)
        api_data = self._get_api_response(login_url, \
        RealStorSideplaneExpanderSensor.LOGIN_HEADERS)
        if api_data:
            session_key = api_data["status"][0]["response"]
        return session_key

    def _get_api_response(self, api_url, headers):
        """performs GET request and returns json response in case of successful
           HTTP request, otherwise returns None"""

        api_json_response = None
        api_response = requests.get(api_url, headers=headers)
        if api_response.status_code == 200:
            api_json_response = json.loads(api_response.text)
        return api_json_response

    def _get_hash(self, username, password):
        """returns a calculated hash required for login"""

        login_credentials = "{0}_{1}".format(username, password)
        hash_value = hashlib.sha256(login_credentials).hexdigest()
        return hash_value

    def _get_faulty_sideplane_expander_list(self):
        """return sideplane expander list using API /show/enclosure"""

        faulty_sideplane_expanders = []
        url = "{0}/show/enclosure".format(self._api_base_url)
        frus = self._get_api_response(url, {"dataType": "json","sessionKey": \
        self._session_key})
        if frus:
            encl_drawers = frus["enclosures"][0]["drawers"]
            if encl_drawers:
                for drawer in encl_drawers:
                    sideplane_list = drawer["sideplanes"]
                    for sideplane in sideplane_list:
                        if sideplane.get("unhealthy-component"):
                            faulty_sideplane_expanders.append(sideplane)
        return faulty_sideplane_expanders

    def _check_for_sideplane_expander_fault(self):
        """iterates over sideplane expander list which has some fault. maintains
           a dictionary in order to keep track of previous health of the FRU, so
           that, alert_type can be set accordingly"""

        try:
            self.unhealthy_components = {}
            self._faulty_sideplane_expander_list = \
            self._get_faulty_sideplane_expander_list()
            alert_type = None
            missing_health = " ".join("Check that all I/O modules and power supplies in\
            the enclosure are fully seated in their slots and that their latches are locked".split())

            for faulty_sideplane_expander in self._faulty_sideplane_expander_list:
                self.unhealthy_components = \
                faulty_sideplane_expander["unhealthy-component"]
                fru_status = faulty_sideplane_expander["health"].lower()
                durable_id = faulty_sideplane_expander["durable-id"].lower()
                health_recommendation = \
                str(self.unhealthy_components[0]["health-recommendation"])

                if fru_status == "fault" and missing_health.strip(" ") in health_recommendation:
                    if durable_id not in self._faulty_sideplane_expander_dict:
                        alert_type = "missing"
                        self._faulty_sideplane_expander_dict[durable_id] = alert_type
                elif fru_status == "fault":
                    if durable_id not in self._faulty_sideplane_expander_dict:
                        alert_type = "fault"
                        self._faulty_sideplane_expander_dict[durable_id] = alert_type
                elif fru_status == "ok":
                    if durable_id in self._faulty_sideplane_expander_dict:
                        previous_alert_type = self._faulty_sideplane_expander_dict.\
                        get(durable_id)
                        if previous_alert_type == "fault":
                            alert_type = "resolved"
                        elif previous_alert_type == "missing":
                            alert_type = "insert"
                        del self._faulty_sideplane_expander_dict[durable_id]
                if alert_type:
                    internal_json_message = self._create_internal_json_message \
                    (faulty_sideplane_expander, self.unhealthy_components, alert_type)
                    self._send_json_message(internal_json_message)
                    alert_type = None
        except Exception as ae:
            logger.exception(ae)

    def _create_internal_json_message(self, sideplane_expander, unhealthy_components, \
        alert_type):
        """creates internal json structure which is sent to realstor_msg_handler
           for further processing"""

        info = {}
        extended_info = {}

        sideplane_unhealthy_components = []

        for unhealthy_component in unhealthy_components:
            del unhealthy_component["component-type-numeric"]
            del unhealthy_component["basetype"]
            del unhealthy_component["meta"]
            del unhealthy_component["primary-key"]
            del unhealthy_component["health-numeric"]
            del unhealthy_component["object-name"]
            sideplane_unhealthy_components.append(unhealthy_component)

        self.sideplane_unhealthy_components = sideplane_unhealthy_components

        info = {
                    "sideplane_expander": {
                        "name": sideplane_expander.get("name"),
                        "status": sideplane_expander.get("status"),
                        "location": sideplane_expander.get("location"),
                        "health": sideplane_expander.get("health"),
                        "health-reason": sideplane_expander.get("health-reason"),
                        "health-recommendation": sideplane_expander.\
                        get("health-recommendation"),
                        "enclosure-id": sideplane_expander.get("enclosure-id"),
                        "unhealthy_components": self.sideplane_unhealthy_components
                    }
               }

        extended_info = {
                            "durable-id": sideplane_expander.get("durable-id"),
                            "drawer-id": sideplane_expander.get("drawer-id"),
                            "position": sideplane_expander.get("position")
                        }

        # create internal json message request structure that will be passed to
        # the StorageEnclHandler
        internal_json_msg = json.dumps(
            {"sensor_request_type" : {
                "enclosure_alert" : {
                        "status": "update",
                        "sensor_type" : RealStorSideplaneExpanderSensor.SENSOR_TYPE,
                        "alert_type": alert_type,
                        "resource_type": RealStorSideplaneExpanderSensor.RESOURCE_TYPE
                    },
                    "info"  : info,
                    "extended_info": extended_info
                    }
            })

        return internal_json_msg

    def _send_json_message(self, json_msg):
        """Transmit data to RealStorMsgHandler to be processed and sent out"""

        # Send the event to real stor message handler to generate json message
        # and send out
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorSideplaneExpanderSensor, self).shutdown()
