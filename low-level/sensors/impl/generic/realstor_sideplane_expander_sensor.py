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
 prohibited. All other rights are expressly reserved by Seagate Technology,
 LLC.
 ****************************************************************************
"""
import hashlib
import json
import os
import errno

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
    SYSTEM_INFORMATION_KEY = "SYSTEM_INFORMATION"
    REALSTORENCLOSURE_KEY = "STORAGE_ENCLOSURE"
    CONTROLLER_IP_KEY = "primary_controller_ip"
    CONTROLLER_PORT_KEY = "primary_controller_port"
    CONTROLLER_USERNAME_KEY = "user"
    CONTROLLER_PASSWORD_KEY = "password"

    RESOURCE_TYPE = "fru"
    SENSOR_TYPE = "enclosure_sideplane_expander_alert"

    # Keys for disk volume to persist faulty FanModule data
    VOLUME_LOCATION_KEY = "data_path"

    # Enclosure directory name
    ENCLOSURE_DIR = "encl"

    # Fan Modules directory name
    SIDEPLANE_EXPANDERS_DIR = "sideplane_expanders"

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
        self._sideplane_expander_list = []
        self._faulty_sideplane_expander_dict = {}

        # Common storage location for RAS
        self._common_storage_location = None

        # Absolute path to store faulty FanModule data including common
        # storage location.
        self._dir_location = None

    def initialize(self, conf_reader, msgQlist, products):
        """Initialize configuration reader and internal msg queues"""

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

        # Get common storage location for persisting data
        self._common_storage_location = \
            self._conf_reader._get_value_with_default(
                self.SYSTEM_INFORMATION_KEY, self.VOLUME_LOCATION_KEY,
                "/var/sspl/data")

        self._api_base_url = "http://{0}:{1}/api".format(self._controller_ip,
                                                         self._controller_port)
        self._api_login_url = "{0}/login".format(self._api_base_url)

        self._dir_location = os.path.join(
            self._common_storage_location, self.ENCLOSURE_DIR,
            "frus", self.SIDEPLANE_EXPANDERS_DIR)

        # Create internal directory structure  if not present
        self._makedirectories(self._dir_location)

        # Persistence file location.
        # This file stores faulty sideplane expander data
        self._faulty_sideplane_expander_file_path = os.path.join(
            self._dir_location, "sideplane_expanders_data.json")

        # Load faulty sideplane expander data from file if available
        self._load_faulty_sideplane_expanders_from_file(
            self._faulty_sideplane_expander_file_path)

        try:
            self._session_key = self._do_login()
        except KeyError as key_error:
            logger.exception(
                "Unable to get session Key: {0}".format(key_error))
        except Exception as exception:
            logger.exception(exception)

    def read_data(self):
        """Returns the current sideplane expander information"""
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
        api_data = self._get_api_response(login_url,
                                          RealStorSideplaneExpanderSensor.
                                          LOGIN_HEADERS)
        if api_data:
            session_key = api_data["status"][0]["response"]
        return session_key

    def _get_api_response(self, api_url, headers):
        """Performs GET request and returns json response in case of successful
           HTTP request, otherwise returns None"""

        api_json_response = None
        api_response = requests.get(api_url, headers=headers)
        if api_response.status_code == 200:
            api_json_response = json.loads(api_response.text)
        return api_json_response

    def _get_hash(self, username, password):
        """Returns a calculated hash required for login"""

        login_credentials = "{0}_{1}".format(username, password)
        hash_value = hashlib.sha256(login_credentials).hexdigest()
        return hash_value

    def _get_sideplane_expander_list(self):
        """Return sideplane expander list using API /show/enclosure"""

        sideplane_expanders = []
        url = "{0}/show/enclosure".format(self._api_base_url)
        frus = self._get_api_response(url, {"dataType": "json", "sessionKey":
                                            self._session_key})
        if frus:
            encl_drawers = frus["enclosures"][0]["drawers"]
            if encl_drawers:
                for drawer in encl_drawers:
                    sideplane_list = drawer["sideplanes"]
                    for sideplane in sideplane_list:
                        sideplane_expanders.append(sideplane)
        return sideplane_expanders

    def _check_for_sideplane_expander_fault(self):
        """Iterates over sideplane expander list which has some fault.
           maintains a dictionary in order to keep track of previous
           health of the FRU, so that, alert_type can be set accordingly"""

        self.unhealthy_components = {}
        self._sideplane_expander_list = \
            self._get_sideplane_expander_list()
        alert_type = None

        missing_health = " ".join("Check that all I/O modules and power supplies in\
        the enclosure are fully seated in their slots and that their latches are locked".split())

        for sideplane_expander in self._sideplane_expander_list:
            try:
                self.unhealthy_components = \
                    sideplane_expander.get("unhealthy-component", [])
                fru_status = sideplane_expander.get("health").lower()
                durable_id = sideplane_expander.get("durable-id").lower()

                if self.unhealthy_components:
                    health_recommendation = \
                        str(self.unhealthy_components[0]
                            ["health-recommendation"])

                if fru_status == "fault" and \
                    missing_health.strip(" ") in health_recommendation:
                    if durable_id not in self._faulty_sideplane_expander_dict:
                        alert_type = "missing"
                        self._faulty_sideplane_expander_dict[durable_id] = \
                            alert_type
                elif fru_status == "fault":
                    if durable_id not in self._faulty_sideplane_expander_dict:
                        alert_type = "fault"
                        self._faulty_sideplane_expander_dict[durable_id] = \
                            alert_type
                elif fru_status == "ok":
                    if durable_id in self._faulty_sideplane_expander_dict:
                        previous_alert_type = \
                            self._faulty_sideplane_expander_dict.get(durable_id)
                        if previous_alert_type == "fault":
                            alert_type = "fault_resolved"
                        elif previous_alert_type == "missing":
                            alert_type = "insertion"
                        del self._faulty_sideplane_expander_dict[durable_id]
                if alert_type:
                    internal_json_message = \
                        self._create_internal_json_message(
                            sideplane_expander, self.unhealthy_components,
                            alert_type)
                    self._send_json_message(internal_json_message)
                    self._save_faulty_sideplane_expanders_to_file(
                        self._faulty_sideplane_expander_file_path)
                    alert_type = None

            except Exception as ae:
                logger.exception(ae)

    def _get_unhealthy_components(self, unhealthy_components):
        """Iterates over each unhealthy components, and creates list with
           required attributes and returns the same list"""

        sideplane_unhealthy_components = []

        for unhealthy_component in unhealthy_components:
            del unhealthy_component["component-type-numeric"]
            del unhealthy_component["basetype"]
            del unhealthy_component["meta"]
            del unhealthy_component["primary-key"]
            del unhealthy_component["health-numeric"]
            del unhealthy_component["object-name"]
            sideplane_unhealthy_components.append(unhealthy_component)

        return sideplane_unhealthy_components

    def _create_internal_json_message(self, sideplane_expander,
                                      unhealthy_components, alert_type):
        """Creates internal json structure which is sent to
           realstor_msg_handler for further processing"""

        sideplane_expander_info_key_list = \
            ['name', 'status', 'location', 'health', 'health-reason',
                'health-recommendation', 'enclosure-id']

        sideplane_expander_extended_info_key_list = \
            ['durable-id', 'drawer-id', 'position']

        sideplane_expander_info_dict = {}
        sideplane_expander_extended_info_dict = {}

        if unhealthy_components:
            sideplane_unhealthy_components = \
                self._get_unhealthy_components(unhealthy_components)

        for exp_key, exp_val in sideplane_expander.items():
            if exp_key in sideplane_expander_info_key_list:
                sideplane_expander_info_dict[exp_key] = exp_val
            if exp_key in sideplane_expander_extended_info_key_list:
                sideplane_expander_extended_info_dict[exp_key] = exp_val

        sideplane_expander_info_dict["unhealthy_components"] = \
            unhealthy_components

        info = {"sideplane_expander":
                dict(sideplane_expander_info_dict.items())}

        extended_info = {"sideplane_expander":
                         sideplane_expander_extended_info_dict}

        # create internal json message request structure that will be passed to
        # the StorageEnclHandler
        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                "enclosure_alert": {
                        "status": "update",
                        "sensor_type":
                        RealStorSideplaneExpanderSensor.SENSOR_TYPE,
                        "alert_type": alert_type,
                        "resource_type":
                        RealStorSideplaneExpanderSensor.RESOURCE_TYPE
                    },
                "info": info,
                "extended_info": extended_info
               }
             })

        return internal_json_msg

    def _save_faulty_sideplane_expanders_to_file(self, filename):
        """Stores previous faulty sideplane expander data instance member
           to file."""

        # Check if filename is blank or None
        if not filename or len(filename.strip()) <= 0:
            logger.critical(
                "No filename is configured to save faulty sideplane data")
            return

        # Check if directory exists
        directory_path = os.path.join(os.path.dirname(filename), "")
        if not os.path.isdir(directory_path):
            logger.critical("Path doesn't exists: {0}".format(directory_path))
            return

        try:
            with open(filename, "w") as sideplane_expander_file:
                json.dump(self._faulty_sideplane_expander_dict,
                          sideplane_expander_file)
        except IOError as io_error:
            error_number = io_error.errno
            if error_number == errno.EACCES:
                logger.critical(
                    "Permission denied for writing to: {0}".format(filename))
            elif error_number == errno.ENOENT:
                logger.critical("File not found: {0}".format(filename))
                logger.exception(io_error)
            else:
                logger.critical("Error in writing file: {0}".format(io_error))
        except Exception as exception:
            logger.exception("Error in writing file: {0}".format(exception))

    def _load_faulty_sideplane_expanders_from_file(self, filename):
        """Loads previous faulty PSU data instance member from file
        if exists.
        """
        if not filename or len(filename.strip()) <= 0:
            logger.critical("No filename is configured to load faulty \
            sideplane expander data from")
            return
        try:
            with open(filename) as sideplane_expander_file:
                data = sideplane_expander_file.read()
                self._faulty_sideplane_expander_dict = json.loads(data)
        except IOError as io_error:
            error_number = io_error.errno
            if error_number == errno.EACCES:
                logger.critical(
                    "Permission denied for reading from {0}".format(filename))
            elif error_number == errno.ENOENT:
                logger.warn(
                    "File not found: {0}. Creating a new...".format(filename))
                self._save_faulty_sideplane_expanders_to_file(
                    self._faulty_sideplane_expander_file_path)
            else:
                logger.critical("Error in reading: {0}".format(io_error))
        except ValueError as value_error:
            logger.critical(value_error)
        except Exception as exception:
            logger.exception("Error in reading file: {0}".format(exception))

    def _makedirectories(self, path):
        """Creates leaf directory with required parents"""

        try:
            os.makedirs(path)
        except OSError as os_error:
            if os_error.errno == errno.EEXIST and os.path.isdir(path):
                pass
            elif os_error.errno == errno.EACCES:
                logger.critical(
                    "Permission denied while creating path: {0}".format(path))
            else:
                raise

    def _send_json_message(self, json_msg):
        """Transmit data to RealStorMsgHandler to be processed and sent out"""

        # Send the event to real stor message handler to generate json message
        # and send out
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorSideplaneExpanderSensor, self).shutdown()
