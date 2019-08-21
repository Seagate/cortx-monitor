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
import json
import os
import errno

import requests
from zope.interface import implements

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from message_handlers.logging_msg_handler import LoggingMsgHandler
from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl

# Modules that receive messages from this module
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler

from sensors.ISideplane_expander import ISideplaneExpandersensor


class RealStorSideplaneExpanderSensor(ScheduledModuleThread, InternalMsgQ):

    implements(ISideplaneExpandersensor)

    SENSOR_NAME = "RealStorSideplaneExpanderSensor"
    SENSOR_TYPE = "enclosure_sideplane_expander_alert"
    RESOURCE_TYPE = "fru"

    PRIORITY = 1

    # Fan Modules directory name
    SIDEPLANE_EXPANDERS_DIR = "sideplane_expanders"

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RealStorSideplaneExpanderSensor.SENSOR_NAME

    def __init__(self):
        super(RealStorSideplaneExpanderSensor, self).__init__(self.SENSOR_NAME,
                                                              self.PRIORITY)

        self.rssencl = singleton_realstorencl

        self._sideplane_expander_list = []
        self._faulty_sideplane_expander_dict = {}

        # sideplane expander persistent cache
        self._sideplane_exp_prcache = None

    def initialize(self, conf_reader, msgQlist, products):
        """Initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RealStorSideplaneExpanderSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RealStorSideplaneExpanderSensor, self).initialize_msgQ(msgQlist)

        self._sideplane_exp_prcache = os.path.join(self.rssencl.frus,\
                                          self.SIDEPLANE_EXPANDERS_DIR)

        # Create internal directory structure  if not present
        self.rssencl.check_prcache(self._sideplane_exp_prcache)

        # Persistence file location.
        # This file stores faulty sideplane expander data
        self._faulty_sideplane_expander_file_path = os.path.join(
            self._sideplane_exp_prcache, "sideplane_expanders_data.json")

        # Load faulty sideplane expander data from file if available
        self._faulty_sideplane_expander_dict = \
            self.rssencl.jsondata.load(\
               self._faulty_sideplane_expander_file_path)

        if self._faulty_sideplane_expander_dict == None:
            self._faulty_sideplane_expander_dict = {}
            self.rssencl.jsondata.dump(\
                self._faulty_sideplane_expander_dict,\
                self._faulty_sideplane_expander_file_path)

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

    def _get_sideplane_expander_list(self):
        """return sideplane expander list using API /show/enclosure"""

        sideplane_expanders = []

        url = self.rssencl.build_url(
                  self.rssencl.URI_CLIAPI_SHOWENCLOSURE)

        response = self.rssencl.ws_request(
                        url, self.rssencl.ws.HTTP_GET)

        if not response:
            logger.warn("{0}:: Enclosure status unavailable as ws request {1}"
                " failed".format(self.rssencl.EES_ENCL, url))
            return

        if response.status_code != self.rssencl.ws.HTTP_OK:
            logger.error("{0}:: http request {1} to get enclosure failed with"
                " err {2}" % self.rssencl.EES_ENCL, url, response.status_code)
            return

        response_data = json.loads(response.text)
        encl_drawers = response_data["enclosures"][0]["drawers"]
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

        if not self._sideplane_expander_list:
            return

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

                if fru_status == self.rssencl.HEALTH_FAULT \
                    and missing_health.strip(" ") in health_recommendation:
                    if durable_id not in self._faulty_sideplane_expander_dict:
                        alert_type = self.rssencl.FRU_MISSING
                        self._faulty_sideplane_expander_dict[durable_id] = alert_type
                elif fru_status == self.rssencl.HEALTH_FAULT:
                    if durable_id not in self._faulty_sideplane_expander_dict:
                        alert_type = self.rssencl.FRU_FAULT
                        self._faulty_sideplane_expander_dict[durable_id] = alert_type
                elif fru_status == self.rssencl.HEALTH_OK:
                    if durable_id in self._faulty_sideplane_expander_dict:
                        previous_alert_type = self._faulty_sideplane_expander_dict.\
                        get(durable_id)
                        if previous_alert_type == self.rssencl.FRU_FAULT:
                            alert_type = self.rssencl.FRU_FAULT_RESOLVED
                        elif previous_alert_type == self.rssencl.FRU_MISSING:
                            alert_type = self.rssencl.FRU_INSERTION
                        del self._faulty_sideplane_expander_dict[durable_id]
                if alert_type:
                    internal_json_message = \
                        self._create_internal_json_message(
                            sideplane_expander, self.unhealthy_components,
                            alert_type)
                    self._send_json_message(internal_json_message)
                    self.rssencl.jsondata.dump(\
                        self._faulty_sideplane_expander_dict,\
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

    def _send_json_message(self, json_msg):
        """Transmit data to RealStorMsgHandler to be processed and sent out"""

        # Send the event to real stor message handler to generate json message
        # and send out
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorSideplaneExpanderSensor, self).shutdown()
