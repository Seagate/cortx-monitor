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
import hashlib
import json

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
        self._faulty_fan_list = {}

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
        return "fan data"

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()
        try:
            self._fan_module_list = self._get_fan_module_list()
            alert_type = None
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

    def _get_fan_list(self):
        """return fan list using API /show/fans"""
        api_fan_list = {}
        url = "{0}/show/fans".format(self._api_base_url)
        api_fan_list = self._get_api_response(url, {"dataType": "json","sessionKey": self._session_key})
        return api_fan_list

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

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorFanSensor, self).shutdown()
