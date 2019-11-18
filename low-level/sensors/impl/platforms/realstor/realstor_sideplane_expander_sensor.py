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
import socket
import time
import uuid

import requests
from zope.interface import implements

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from message_handlers.logging_msg_handler import LoggingMsgHandler
from framework.platforms.realstor.realstor_enclosure import singleton_realstorencl

# Modules that receive messages from this module
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler

from sensors.ISideplane_expander import ISideplaneExpandersensor


class RealStorSideplaneExpanderSensor(ScheduledModuleThread, InternalMsgQ):

    implements(ISideplaneExpandersensor)

    SENSOR_NAME = "RealStorSideplaneExpanderSensor"
    SENSOR_TYPE = "enclosure_sideplane_expander_alert"
    RESOURCE_TYPE = "enclosure:fru:sideplane"

    PRIORITY = 1

    # Fan Modules directory name
    SIDEPLANE_EXPANDERS_DIR = "sideplane_expanders"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RealStorEnclMsgHandler"],
                    "rpms": []
    }

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

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return RealStorSideplaneExpanderSensor.DEPENDENCIES

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
            if url.find(self.rssencl.ws.LOOPBACK) == -1:
                logger.error("{0}:: http request {1} to get enclosure failed with"
                    " err {2}".format(self.rssencl.EES_ENCL, url, response.status_code))
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
        unhealthy_component = {}

        unhealthy_component_list = ['health', 'health-reason',
                                        'health-recommendation', 'component-id']

        for unhealthy_component in unhealthy_components:
            for unhealthy_key in filter(lambda common_key: common_key in unhealthy_component, unhealthy_component_list):
                unhealthy_component[unhealthy_key] = unhealthy_component.get(unhealthy_key, "")
            sideplane_unhealthy_components.append(unhealthy_component)

        return sideplane_unhealthy_components

    def _create_internal_json_message(self, sideplane_expander,
                                      unhealthy_components, alert_type):
        """Creates internal json structure which is sent to
           realstor_msg_handler for further processing"""

        sideplane_expander_info_key_list = \
            ['name', 'status', 'location', 'health', 'health-reason',
                'health-recommendation', 'enclosure-id',
                'durable-id', 'drawer-id', 'position']

        sideplane_expander_info_dict = {}

        if unhealthy_components:
            sideplane_unhealthy_components = \
                self._get_unhealthy_components(unhealthy_components)

        for exp_key, exp_val in sideplane_expander.items():
            if exp_key in sideplane_expander_info_key_list:
                sideplane_expander_info_dict[exp_key] = exp_val

        sideplane_expander_info_dict["unhealthy_components"] = \
            unhealthy_components

        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        drawer_id = "drawer" + ' ' + str(sideplane_expander_info_dict.get("drawer-id"))
        name = sideplane_expander_info_dict.get("name", "")
        resource_id = drawer_id + ' ' + name
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
                        "status": "update",
                        "host_id": host_name,
                        "alert_type": alert_type,
                        "alert_id": alert_id,
                        "severity": severity,
                        "info": info,
                        "specific_info": sideplane_expander_info_dict
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

        # Send the event to real stor message handler to generate json message
        # and send out
        self._write_internal_msgQ(RealStorEnclMsgHandler.name(), json_msg)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RealStorSideplaneExpanderSensor, self).shutdown()
