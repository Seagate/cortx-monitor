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
 prohibited. All other rights are expressly reserved by Seagate Technology,
 LLC.
 ****************************************************************************
"""
import errno
import json
import os
import re
import socket
import time
import uuid

import requests
from zope.interface import implementer

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from message_handlers.logging_msg_handler import LoggingMsgHandler
from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl
from framework.utils.store_factory import store

# Modules that receive messages from this module
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler

from sensors.Ifan import IFANsensor

@implementer(IFANsensor)
class RealStorFanSensor(ScheduledModuleThread, InternalMsgQ):


    SENSOR_NAME = "RealStorFanSensor"
    SENSOR_TYPE = "enclosure_fan_module_alert"
    RESOURCE_TYPE = "enclosure:fru:fan"

    PRIORITY = 1

    # Fan Modules directory name
    FAN_MODULES_DIR = "fanmodules"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RealStorEnclMsgHandler"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorFanSensor.SENSOR_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return RealStorFanSensor.DEPENDENCIES

    def __init__(self):
        super(RealStorFanSensor, self).__init__(self.SENSOR_NAME,
                                                self.PRIORITY)
        self.rssencl = singleton_realstorencl

        self._faulty_fan_file_path = None
        self._faulty_fan_modules_list = {}
        self._fan_modules_list = {}

        # fan modules psus persistent cache
        self._fanmodule_prcache = None

        # Flag to indicate suspension of module
        self._suspended = False

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorFanSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorFanSensor, self).initialize_msgQ(msgQlist)


        self._fanmodule_prcache = os.path.join(self.rssencl.frus, \
                                      self.FAN_MODULES_DIR)

        # Create internal directory structure  if not present
        self.rssencl.check_prcache(self._fanmodule_prcache)

        # Persistence file location. This file stores faulty FanModule data
        self._faulty_fan_file_path = os.path.join(
            self._fanmodule_prcache, "fanmodule_data.json")

        # Load faulty Fan Module data from file if available
        self._faulty_fan_modules_list = store.get(\
                                           self._faulty_fan_file_path)

        if self._faulty_fan_modules_list == None:
            self._faulty_fan_modules_list = {}
            store.put(self._faulty_fan_modules_list,\
                self._faulty_fan_file_path)

    def read_data(self):
        """Return the Current fan_module information"""
        return self._fan_modules_list

    def run(self):
        """Run the sensor on its own thread"""

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(30, self._priority, self.run, ())
            return

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        # Periodically check if there is any fault in the fan_module
        self._check_for_fan_module_fault()

        self._scheduler.enter(30, self._priority, self.run, ())

    def _check_for_fan_module_fault(self):
        """Iterates over fan modules list. maintains a dictionary in order to
           keep track of previous health of the FRU in order to set
           alert_type"""

        self._fan_modules_list = self._get_fan_modules_list()
        alert_type = None

        if not self._fan_modules_list:
            return

        try:
            for fan_module in self._fan_modules_list:
                fru_status = fan_module.get("health").lower()
                durable_id = fan_module.get("durable-id").lower()
                health_reason = fan_module.get("health-reason").lower()

                if fru_status == self.rssencl.HEALTH_FAULT and \
                    self._check_if_fan_module_is_installed(health_reason):
                    if durable_id not in self._faulty_fan_modules_list:
                        alert_type = self.rssencl.FRU_MISSING
                        self._faulty_fan_modules_list[durable_id] = alert_type
                    else:
                        prev_alert_type = self._faulty_fan_modules_list[durable_id]
                        if prev_alert_type != self.rssencl.FRU_MISSING:
                            alert_type = self.rssencl.FRU_MISSING
                            self._faulty_fan_modules_list[durable_id] = alert_type
                elif fru_status == self.rssencl.HEALTH_FAULT or \
                         fru_status == self.rssencl.HEALTH_DEGRADED:
                    if durable_id not in self._faulty_fan_modules_list:
                        alert_type = self.rssencl.FRU_FAULT
                        self._faulty_fan_modules_list[durable_id] = alert_type
                    else:
                        prev_alert_type = self._faulty_fan_modules_list[durable_id]
                        if prev_alert_type != self.rssencl.FRU_FAULT:
                            alert_type = self.rssencl.FRU_FAULT
                            self._faulty_fan_modules_list[durable_id] = alert_type
                elif fru_status == self.rssencl.HEALTH_OK:
                    if durable_id in self._faulty_fan_modules_list:
                        prev_alert_type = \
                            self._faulty_fan_modules_list[durable_id]
                        if prev_alert_type == self.rssencl.FRU_MISSING:
                            alert_type = self.rssencl.FRU_INSERTION
                        else:
                            alert_type = self.rssencl.FRU_FAULT_RESOLVED
                        del self._faulty_fan_modules_list[durable_id]

                # Persist faulty Fan Module list to file only if there is any
                # type of alert generated
                if alert_type:
                    internal_json_message = \
                        self._create_internal_json_msg(fan_module, alert_type)
                    self._send_json_message(internal_json_message)
                    store.put(self._faulty_fan_modules_list,\
                        self._faulty_fan_file_path)
                    alert_type = None
        except Exception as e:
            logger.exception(e)

    def _check_if_fan_module_is_installed(self, health_reason):
        """ This function returns true if given string contains substring
            otherwise, it returns false. To achieve this, it uses search
            method of python re module"""

        not_installed_health_string = "not installed"
        return bool(re.search(not_installed_health_string, health_reason))

    def _get_fan_modules_list(self):
        """Returns fan module list using API /show/fan-modules"""

        url = self.rssencl.build_url(
                  self.rssencl.URI_CLIAPI_SHOWFANMODULES)

        response = self.rssencl.ws_request(
                        url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Fan-modules status unavailable as ws request {1}"
                            "failed".format(self.rssencl.EES_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error(
                    "{0}:: http request {1} to get fan-modules failed with http err"
                    " {2}".format(self.rssencl.EES_ENCL, url, response.status_code))
            return

        response_data = json.loads(response.text)

        fan_modules_list = response_data["fan-modules"]
        return fan_modules_list

    def _get_fan_attributes(self, fan_module):
        """Returns individual fan attributes from each fan-module"""

        fan_list = []
        fans = {}
        fan_key = ""

        fan_attribute_list = [ 'status', 'name', 'speed', 'durable-id',
            'health', 'fw-revision', 'health-reason', 'serial-number',
                'location', 'position', 'part-number', 'health-recommendation',
                    'hw-revision', 'locator-led' ]

        fru_fans = fan_module.get("fan", [])

        for fan in fru_fans:
            for fan_key in filter(lambda common_key: common_key in fan_attribute_list, fan):
                fans[fan_key] = fan.get(fan_key)
            fan_list.append(fans)
        return fan_list

    def _create_internal_json_msg(self, fan_module, alert_type):
        """Creates internal json structure which is sent to
            realstor_msg_handler for further processing"""

        fan_module_info_key_list = \
            ['name', 'location', 'status', 'health',
                'health-reason', 'health-recommendation', 'enclosure-id',
                'durable-id', 'position']

        fan_module_info_dict = {}
        fan_module_extended_info_dict = {}

        fans_list = self._get_fan_attributes(fan_module)

        for fan_module_key, fan_module_value in fan_module.items():
            if fan_module_key in fan_module_info_key_list:
                fan_module_info_dict[fan_module_key] = fan_module_value

        fan_module_info_dict["fans"] = fans_list

        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        resource_id = fan_module_info_dict.get("name", "")
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
                        "specific_info": fan_module_info_dict
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

    def _send_json_message(self, json_msg):
        """Transmit data to RealStorMsgHandler to be processed and sent out"""

        # Send the event to real stor message handler
        # to generate json message and send out
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    # TODO: Need to change IEM Message Format
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
                }}, sort_keys=True)

        # Send the event to real stor message handler
        # to generate json message and send out
        internal_json_msg = json.dumps(
                {'actuator_request_type':
                    {'logging':
                        {'log_level': 'LOG_WARNING', 'log_type': 'IEM',
                            'log_msg': '{}'.format(json_data)}}})

        # Send the event to logging msg handler to send IEM message to journald
        #self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RealStorFanSensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RealStorFanSensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorFanSensor, self).shutdown()
