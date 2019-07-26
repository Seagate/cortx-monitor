"""
 ****************************************************************************
 Filename:          relstor_fan_sensor.py
 Description:       Monitors FAN data using RealStor API
 Creation Date:     07/06/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import errno
import hashlib
import json
import os

import requests
from zope.interface import implements

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from message_handlers.logging_msg_handler import LoggingMsgHandler
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from sensors.Ifan import IFANsensor


class RealStorFanSensor(ScheduledModuleThread, InternalMsgQ):

    implements(IFANsensor)

    SENSOR_NAME = "RealStorFanSensor"
    PRIORITY = 1

    LOGIN_HEADERS = {"dataType": "json"}

    # sspl configuration keys
    REALSTORENCLOSURE_KEY = "STORAGE_ENCLOSURE"
    CONTROLLER_IP_KEY = "primary_controller_ip"
    CONTROLLER_PORT_KEY = "primary_controller_port"
    CONTROLLER_USERNAME_KEY = "user"
    CONTROLLER_PASSWORD_KEY = "password"

    RESOURCE_TYPE = "fru"
    SENSOR_TYPE = "enclosure_fan_alert"

    # Keys for disk volume to persist faulty FanModule data
    VOLUME_LOCATION_KEY = "data_path"

    SYSTEM_INFORMATION_KEY = "SYSTEM_INFORMATION"

    # Enclosure directory name
    ENCLOSURE_DIR = "encl"


    # Fan Modules directory name
    FAN_MODULES_DIR = "fanmodules"

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorFanSensor.SENSOR_NAME

    def __init__(self):
        super(RealStorFanSensor, self).__init__(self.SENSOR_NAME,
                                         self.PRIORITY)

        self._controller_ip = None
        self._port = None
        self._username = None
        self._password = None
        self._api_base_url = None
        self._api_login_url = None
        self._session_key = None
        self._fan_list = {}
        self._faulty_fan_file_path = None
        self._faulty_fan_list = {}
        self._common_storage_location = None  # Common storage location for RAS

        # Absolute path to store faulty FanModule data including common
        # storage location.
        self._dir_location = None

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorFanSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorFanSensor, self).initialize_msgQ(msgQlist)

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
            "frus", self.FAN_MODULES_DIR)

        # Create internal directory structure  if not present
        self._makedirectories(self._dir_location)
        # Persistence file location. This file stores faulty FanModule data
        self._faulty_fan_file_path = os.path.join(
            self._dir_location, "fanmodule_data.json")

        # Load faulty Fan Module data from file if available
        self._load_faulty_fan_modules_from_file(self._faulty_fan_file_path)
        try:
            self._session_key = self._do_login()
        except KeyError as key_error:
            logger.exception("Unable to get session Key: {0}".format(key_error))
        except Exception as exception:
            logger.exception(exception)

    def read_data(self):
        """Return the Current RAID status information"""
        return "fan data"

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()
        try:
            self._fan_module_list = self._get_fan_module_list()
            alert_type = None
            # Flag to indicate if there is a change in _faulty_fan_list
            state_changed = False
            for fan_module in self._fan_module_list:
                serial_number = fan_module["serial-number"]
                fru_status = fan_module["fru-status"]
                slot = int(fan_module["fru-location"].split(" ")[3])
                if fru_status == "Fault":
                     if slot not in self._faulty_fan_list:
                        self._faulty_fan_list[slot] = { "serial-number": serial_number }
                        alert_type = "missing"
                elif fru_status == "OK":
                    if slot in self._faulty_fan_list:
                        if serial_number in self._faulty_fan_list[slot]["serial-number"]:
                            alert_type = "fault_resolved"
                        else:
                            alert_type = "insertion"
                        del self._faulty_fan_list[slot]
                if alert_type:
                    internal_json_message = self._create_internal_json_message(fan_module, alert_type)
                    self._send_json_message(internal_json_message)
                    alert_type = None
                # Persist faulty Fan Module list to file only if something is changed
                if state_changed:
                    self._save_faulty_fan_modules_to_file(self._faulty_fan_file_path)
                    state_changed = False
        except Exception as ae:
            logger.exception(ae)

        self._scheduler.enter(30, self._priority, self.run, ())

    def _do_login(self):
        """Logs in into the system through API and returns session key"""

        session_key = None
        hash_val = self._get_hash(self._username, self._password)
        login_url = "{0}/{1}".format(self._api_login_url, hash_val)
        api_data = self._get_api_response(login_url, RealStorFanSensor.LOGIN_HEADERS)
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

    def _get_fan_module_list(self):
        """return fan module list using API /show/frus"""

        api_fan_module_list = {}
        fan_module_list = []
        url = "{0}/show/frus".format(self._api_base_url)
        api_frus = self._get_api_response(url, {"dataType": "json","sessionKey": self._session_key})
        if api_frus:
            api_fru_list = api_frus["enclosure-fru"]
            for fru in api_fru_list:
                if fru["name"] == "FAN MODULE":
                    fan_module_list.append(fru)
            api_fan_module_list = fan_module_list
        return api_fan_module_list

    def _create_internal_json_message(self, fan_module, alert_type):
        """creates internal json structure which is sent to realstor_msg_handler
           for further processing"""

        info = {
                    "name": fan_module.get("name"),
                    "description": fan_module.get("description"),
                    "part-number": fan_module.get("part-number"),
                    "serial-number": fan_module.get("serial-number"),
                    "revision": fan_module.get("revision"),
                    "mfg-date": fan_module.get("mfg-date"),
                    "mfg-vendor-id": fan_module.get("mfg-vendor-id"),
                    "fru-location": fan_module.get("fru-location"),
                    "fru-status": fan_module.get("fru-status"),
                    "enclosure-id": fan_module.get("enclosure-id")
               }

        extended_info = {
                            "configuration-serial-number": fan_module.get("configuration-serialnumber")
                        }

        # create internal json message request structure that will be passed to the StorageEnclHandler
        internal_json_msg = json.dumps(
            {"sensor_request_type" : {
                "enclosure_alert" : {
                        "status": "update",
                        "sensor_type" : RealStorFanSensor.SENSOR_TYPE,
                        "alert_type": alert_type,
                        "resource_type": RealStorFanSensor.RESOURCE_TYPE
                    },
                    "info"  : info,
                    "extended_info": extended_info
                    }
            })

        return internal_json_msg

    def _send_json_message(self, json_msg):
        """Transmit data to RealStorMsgHandler to be processed and sent out"""

        # Send the event to real stor message handler to generate json message and send out
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    def _log_IEM(self, info, extended_info):
        """Sends an IEM to logging msg handler"""
        json_data = json.dumps(
            {"sensor_request_type": {
                "enclosure_alert": {
                        "status": "update",
                        "sensor_type": RealStorFanSensor.SENSOR_TYPE,
                        "resource_type": RealStorFanSensor.RESOURCE_TYPE
                    },
                    "info": info,
                    "extended_info": extended_info
                    }
                }, sort_keys=True)

        # Send the event to real stor message handler to generate json message and send out
        internal_json_msg=json.dumps(
                {'actuator_request_type': {'logging': {'log_level': 'LOG_WARNING', 'log_type': 'IEM', 'log_msg': '{}'.format(json_data)}}})

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def _save_faulty_fan_modules_to_file(self, filename):
        """Stores previous faulty Fan Module data to file"""

        # Check if filename is blank or None
        if not filename or len(filename.strip()) <= 0:
            logger.critical("No filename is configured to save faulty fan module data")
            return

        # Check if directory exists
        directory_path = os.path.join(os.path.dirname(filename), "")
        if not os.path.isdir(directory_path):
            logger.critical("Path doesn't exists: {0}".format(directory_path))
            return

        try:
            with open(filename, "w") as fan_module_file:
                json.dump(self._faulty_fan_list, fan_module_file)
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

    def _load_faulty_fan_modules_from_file(self, filename):
        """Loads previous faulty Fan Module data from file if exists"""
        if not filename or len(filename.strip()) <= 0:
            logger.critical("No filename is configured to load faulty Fan Module data from")
            return
        try:
            with open(filename) as fan_module_file:
                data = fan_module_file.read()
                self._faulty_fan_list = json.loads(data)
        except IOError as io_error:
            error_number = io_error.errno
            if error_number == errno.EACCES:
                logger.critical(
                    "Permission denied for reading from {0}".format(filename))
            elif error_number == errno.ENOENT:
                logger.warn(
                    "File not found: {0}. Creating a new...".format(filename))
                self._save_faulty_fan_modules_to_file(self._faulty_fan_file_path)
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
        super(RealStorFanSensor, self).shutdown()
