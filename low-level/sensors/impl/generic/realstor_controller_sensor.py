"""
 ****************************************************************************
 Filename:          realstor_controller_sensor.py
 Description:       Monitors Controller data using RealStor API.
 Creation Date:     07/17/2019
 Author:            Satish Darade

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
import errno
import os

import requests
from zope.interface import implements

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from sensors.Icontroller import IControllersensor


class RealStorControllerSensor(ScheduledModuleThread, InternalMsgQ):
    """Monitors Controller data using RealStor API"""

    implements(IControllersensor)

    SENSOR_NAME = "RealStorControllerSensor"
    PRIORITY = 1

    STORAGE_ENCLOSURE_KEY = "STORAGE_ENCLOSURE"
    SYSTEM_INFORMATION_KEY = "SYSTEM_INFORMATION"

    # Keys for connections
    CONTROLLER_IP_KEY = "primary_controller_ip"
    PORT_KEY = "primary_controller_port"

    # Keys for credentials
    CONTROLLER_USERNAME_KEY = "user"
    CONTROLLER_PASSWORD_KEY = "password"

    # Keys for disk volume to persist faulty Controller data
    VOLUME_LOCATION_KEY = "data_path"

    # Enclosure directory name
    ENCLOSURE_DIR = "encl"

    # Controllers directory name
    CONTROLLERS_DIR = "controllers"

    #generic fields list
    controller_generic = ["object-name", "controller-id", "serial-number", "hardware-version",
                          "position", "cpld-version", "mac-address", "node-wwn", "ip-address",
                          "ip-subnet-mask", "ip-gateway", "disks", "number-of-storage-pools",
                          "virtual-disks", "host-ports", "drive-channels", "drive-bus-type",
                          "status", "failed-over", "fail-over-reason", "vendor", "model",
                          "platform-type", "write-policy", "description", "part-number",
                          "revision", "mfg-vendor-id", "locator-led", "health", "health-reason",
                          "redundancy-mode", "redundancy-status"]

    network_generic = ["link-speed", "duplex-mode", "health", "health-reason"]

    port_generic = ["controller", "port", "port-type", "media", "target-id", "status",
                    "actual-speed", "configured-speed", "health", "health-reason",
                    "health-recommendation"]

    fc_port_generic = ["configured-topology", "sfp-status", "sfp-present", "sfp-vendor",
                       "sfp-part-number", "sfp-revision", "sfp-supported-speeds"]

    expander_ports_generic = ["enclosure-id", "controller", "sas-port-type", "sas-port-index",
                              "name", "status", "health", "health-reason", "health-recommendation"]

    compact_flash_generic = ["controller-id", "name", "status", "cache-flush", "health",
                             "health-reason", "health-recommendation"]

    expanders_generic = ["enclosure-id", "drawer-id", "name", "location", "status",
                         "extended-status", "fw-revision", "health", "health-reason",
                         "health-recommendation"]

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorControllerSensor.SENSOR_NAME

    def __init__(self):
        super(RealStorControllerSensor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)

        self._controller_ip = None
        self._port = None
        self._api_base_url = None
        self._login_url = None
        self._username = None
        self._password = None
        self._session_key = None
        self._faulty_controller_file_path = None
        self._common_storage_location = None  # Common storage location for RAS

        # Absolute path to store faulty Controller data including common
        # storage location.
        self._dir_location = None

        # Holds Controllers with faults. Used for future reference.
        self._previously_faulty_controllers = {}

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorControllerSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorControllerSensor, self).initialize_msgQ(msgQlist)

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

        # Get common storage location for persisting data
        self._common_storage_location = \
            self._conf_reader._get_value_with_default(
                self.SYSTEM_INFORMATION_KEY, self.VOLUME_LOCATION_KEY,
                "/var/sspl/data")

        # Form an base API and login URL
        self._api_base_url = "http://{0}:{1}/api".format(
            self._controller_ip, self._port)
        self._login_url = "{0}/login".format(self._api_base_url)

        self._dir_location = os.path.join(
            self._common_storage_location, self.ENCLOSURE_DIR, "frus", self.CONTROLLERS_DIR)

        # Create internal directory structure  if not present
        self._makedirectories(self._dir_location)

        # Persistence file location. This file stores faulty Controller data
        self._faulty_controller_file_path = os.path.join(
            self._dir_location, "controllerdata.json")

        # Load faulty Controller data from file if available
        self._load_faulty_controllers_from_file(self._faulty_controller_file_path)
        try:
            self._session_key = self._login(self._username, self._password)
        except KeyError as key_error:
            logger.exception("Key not found: {0}".format(key_error))
        except Exception as exception:
            logger.exception(exception)

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        controllers = None
        try:
            controllers = self._get_controllers(
                {"sessionKey": self._session_key, "dataType": "json"})
            self._get_msgs_for_faulty_controllers(controllers)
        except Exception as exception:
            logger.exception(exception)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 10 seconds to see if We have a faulty Controller
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

    def _get_controllers(self, headers):
        """Receives list of Controllers from API.
           URL: http://<host>/api/show/controllers
        """
        controller_url = "{0}/show/controllers".format(self._api_base_url)
        response = self._get_data(controller_url, headers)
        controllers = response.get("controllers")
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
        for controller in controllers:
            controller_health = controller["health"].lower()
            controller_status = controller["status"].lower()
            durable_id = controller["durable-id"]
            if controller_health == "fault":  # Check for missing and fault case
                if durable_id not in self._previously_faulty_controllers:
                    alert_type = "fault"
                    # Check for removal
                    if controller_status == "not installed":
                        alert_type = "missing"
                    self._previously_faulty_controllers[durable_id] = {
                        "health": controller_health, "alert_type": alert_type}
                    state_changed = True
                    internal_json_msg = self._create_internal_msg(
                        controller, alert_type)
                    faulty_controller_messages.append(internal_json_msg)
                    # Send message to handler
                    if send_message:
                        self._send_json_msg(internal_json_msg)
            elif controller_health == "degraded":  # Check for fault case
                if durable_id not in self._previously_faulty_controllers:
                    alert_type = "fault"
                    self._previously_faulty_controllers[durable_id] = {
                        "health": controller_health, "alert_type": alert_type}
                    state_changed = True
                    internal_json_msg = self._create_internal_msg(
                        controller, alert_type)
                    faulty_controller_messages.append(internal_json_msg)
                    # Send message to handler
                    if send_message:
                        self._send_json_msg(internal_json_msg)
            elif controller_health == "ok":  # Check for healthy case
                if durable_id in self._previously_faulty_controllers:
                    # Send message to handler
                    if send_message:
                        previous_alert_type = \
                            self._previously_faulty_controllers[durable_id]["alert_type"]
                        alert_type = "fault_resolved"
                        if previous_alert_type == "missing":
                            alert_type = "insertion"
                        internal_json_msg = self._create_internal_msg(
                            controller, alert_type)
                        faulty_controller_messages.append(internal_json_msg)
                        if send_message:
                            self._send_json_msg(internal_json_msg)
                    del self._previously_faulty_controllers[durable_id]
                    state_changed = True
            # Persist faulty Controller list to file only if something is changed
            if state_changed:
                self._save_faulty_controllers_to_file(self._faulty_controller_file_path)
                state_changed = False
            alert_type = ""
        return faulty_controller_messages

    def _create_internal_msg(self, controller_detail, alert_type):
        """Forms a dictionary containing info about Controllers to send to
           message handler.
        """
        if not controller_detail:
            return {}

        generic_dict={}
        extended_dict={}
        #TODO Need to optimizing nested for look code here
        for key, value in controller_detail.iteritems():
            if key == "expander-ports":
                expndr_ports_gen_dict, expndr_ports_ext_dict=self._get_nested_controller_data(
                    "expander_port", controller_detail[key])
                generic_dict.update(expndr_ports_gen_dict)
                extended_dict.update(expndr_ports_ext_dict)
            elif key == "port":
                port_gen_dict, port_ext_dict = self._get_nested_controller_data(
                    "port",controller_detail[key])
                generic_dict.update(port_gen_dict)
                extended_dict.update(port_ext_dict)
            elif key == "network-parameters":
                network_gen_dict, network_ext_dict = self._get_nested_controller_data(
                    "network",controller_detail['network-parameters'])
                generic_dict.update(network_gen_dict)
                extended_dict.update(network_ext_dict)
            elif key == "compact-flash":
                compact_gen_dict, compact_ext_dict = self._get_nested_controller_data(
                    "compact_flash",controller_detail[key])
                generic_dict.update(compact_gen_dict)
                extended_dict.update(compact_ext_dict)
            elif key == "expanders":
                expanders_gen_dict, expanders_ext_dict = self._get_nested_controller_data(
                    "expanders",controller_detail[key])
                generic_dict.update(expanders_gen_dict)
                extended_dict.update(expanders_ext_dict)
            else:
                if key in self.controller_generic:
                    generic_dict.update({key:value})
                else:
                    extended_dict.update({key:value})

        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                    "enclosure_alert": {
                        "sensor_type" : "enclosure_controller_alert",
                        "resource_type": "fru",
                        "alert_type": alert_type,
                        "status": "update"
                    },
                    "info": generic_dict,
                    "extended_info": extended_dict
            }})
        return internal_json_msg

    def _get_nested_controller_data(self, prefix, lstdict):
        generic_nested_dict={}
        expanded_nested_dict={}
        for idx,nested_dict in enumerate(lstdict):
            for key, value in nested_dict.iteritems():
                if key == "fc-port":
                    fc_port_gen_dict, fc_port_exp_dict = self._get_fc_port_controller_data(
                        prefix+"."+str(idx)+".fc", nested_dict[key])
                    generic_nested_dict.update(fc_port_gen_dict)
                    expanded_nested_dict.update(fc_port_exp_dict)
                elif key == "sas-port":
                    sas_port_exp_dict = self._get_sas_port_controller_data(
                        prefix+"."+str(idx)+".sas", nested_dict[key])
                    expanded_nested_dict.update(sas_port_exp_dict)
                else:
                    if prefix == "expander_port":
                        if key in self.expander_ports_generic:
                            generic_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                        else:
                            expanded_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                    elif prefix == "port":
                        if key in self.port_generic:
                            generic_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                        else:
                            expanded_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                    elif prefix == "network":
                        if key in self.network_generic:
                            generic_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                        else:
                            expanded_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                    elif prefix == "compact_flash":
                        if key in self.compact_flash_generic:
                            generic_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                        else:
                            expanded_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                    elif prefix == "expanders":
                        if key in self.expanders_generic:
                            generic_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
                        else:
                            expanded_nested_dict.update({prefix+"."+str(idx)+"."+key : value})
        return generic_nested_dict, expanded_nested_dict

    def _get_fc_port_controller_data(self, prefix, lstdict):
        fc_port_generic_dic = {}
        fc_port_expande_dic = {}
        for idx,nested_fc_dict in enumerate(lstdict):
            for key, value in nested_fc_dict.iteritems():
                if key in self.fc_port_generic:
                    fc_port_generic_dic.update({prefix+"."+str(idx)+"."+key : value})
                else:
                    fc_port_expande_dic.update({prefix+"."+str(idx)+"."+key : value})
        return fc_port_generic_dic, fc_port_expande_dic

    def _get_sas_port_controller_data(self, prefix, lstdict):
        sas_port_expande_dic = {}
        for idx,nested_sas_dict in enumerate(lstdict):
            for key, value in nested_sas_dict.iteritems():
                sas_port_expande_dic.update({prefix+"."+str(idx)+"."+key : value})
        return sas_port_expande_dic

    def _send_json_msg(self, json_msg):
        """Sends JSON message to Handler"""
        if not json_msg:
            return
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    def _save_faulty_controllers_to_file(self, filename):
        """Stores previous faulty Controller data instance member to file.
        """
        # Check if filename is blank or None
        if not filename or len(filename.strip()) <= 0:
            logger.critical("No filename is configured to save faulty Controller data")
            return

        # Check if directory exists
        directory_path = os.path.join(os.path.dirname(filename), "")
        if not os.path.isdir(directory_path):
            logger.critical("Path doesn't exists: {0}".format(directory_path))
            return

        try:
            with open(filename, "w") as controller_file:
                json.dump(self._previously_faulty_controllers, controller_file)
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

    def _load_faulty_controllers_from_file(self, filename):
        """Loads previous faulty Controller data instance member from file
        if exists.
        """
        if not filename or len(filename.strip()) <= 0:
            logger.critical("No filename is configured to save faulty Controller from")
            return
        try:
            with open(filename) as controller_file:
                data = controller_file.read()
                self._previously_faulty_controllers = json.loads(data)
        except IOError as io_error:
            error_number = io_error.errno
            if error_number == errno.EACCES:
                logger.critical(
                    "Permission denied for reading from {0}".format(filename))
            elif error_number == errno.ENOENT:
                logger.warn(
                    "File not found: {0}. Creating a new...".format(filename))
                self._save_faulty_controllers_to_file(self._faulty_controller_file_path)
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

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorControllerSensor, self).shutdown()
