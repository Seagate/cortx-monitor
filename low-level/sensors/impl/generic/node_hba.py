# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com

import errno
import json
import os
import time
import uuid
from zope.interface import implementer

from framework.base.debug import Debug
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from framework.base.sspl_constants import DATA_PATH, SAS_RESOURCE_ID
from framework.utils.conf_utils import (GLOBAL_CONF, SSPL_CONF, Conf,
    NODE_ID_KEY)
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from framework.utils.store_factory import file_store
from framework.utils.tool_factory import ToolFactory
from framework.utils.os_utils import OSUtils
from framework.utils.mon_utils import MonUtils
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from framework.messaging.egress_processor import EgressProcessor
from framework.platforms.server.component_factory import ServerCompFactory
from json_msgs.messages.sensors.hba_data import HBADataMsg
from sensors.Ihba import IHBASensor

# Override default store
store = file_store


@implementer(IHBASensor)
class HBASensor(SensorThread, InternalMsgQ):
    """
    HBA sensor which runs on its own thread periodically and
    is responsible for sensing events like HBA card insertion,
    removable, host port running and not running.
    """

    SENSOR_NAME = "HBASensor"
    PRIORITY = 1

    HBA_RESOURCE_TYPE = "node:hw:hba"
    HBA_PORT_RESOURCE_TYPE = "node:hw:hba:port"

    # FRU alert types
    FRU_MISSING = "missing"
    FRU_INSERTION = "insertion"
    FRU_FAULT = "fault"
    FRU_FAULT_RESOLVED = "fault_resolved"

    FRU_ALERTS = [FRU_MISSING, FRU_INSERTION, FRU_FAULT, FRU_FAULT_RESOLVED]

    # Section in the configuration store
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    POLLING_INTERVAL = "polling_interval"

    CACHE_DIR_NAME  = "server"
    DEFAULT_POLLING_INTERVAL = '20'
    PROBE = "probe"

    # Dependency list
    DEPENDENCIES = {
            "plugins": ["NodeControllerMsgHandler", "EgressProcessor"],
            "rpms": []
        }


    @staticmethod
    def name():
        """@return: name of the module."""
        return HBASensor.SENSOR_NAME


    @staticmethod
    def impact():
        """Returns impact of the module."""
        return "Server HBA card and initiators can not be monitored."


    def __init__(self, utility_instance=None):
        """Initialize HBA sensor instance."""
        super(HBASensor, self).__init__(self.SENSOR_NAME, self.PRIORITY)
        self._utility_instance = utility_instance
        self._hba = None
        self.hosts = []
        self.host_data = []
        self.hba_data_msg = None

        # Flag to indicate suspension of module
        self._suspended = False


    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(HBASensor, self).initialize(conf_reader)
        super(HBASensor, self).initialize_msgQ(msgQlist)

        # Get the hba implementor from configuration
        hba_utility = Conf.get(SSPL_CONF,
            f"{self.name().upper()}>{self.PROBE}", "sysfs")

        self.polling_interval = int(Conf.get(SSPL_CONF,
            f"{self.SENSOR_NAME.upper()}>{self.POLLING_INTERVAL}",
            self.DEFAULT_POLLING_INTERVAL))

        self._node_id = Conf.get(GLOBAL_CONF, NODE_ID_KEY, 'SN01')

        cache_dir_path = os.path.join(DATA_PATH, self.CACHE_DIR_NAME)
        self.HBA_SENSOR_DATA = os.path.join(
            cache_dir_path, f'HBA_SENSOR_DATA_{self._node_id}')

        # Get the stored previous alert info
        self.stored_hba_status = store.get(self.HBA_SENSOR_DATA)

        # Initialize HBA utility
        self._hba = ServerCompFactory.get_instance("HBA")

        try:
            self._hba.initialize_utility(hba_utility)
        except KeyError as key_error:
            raise Exception(f"Unable to initialize HBA utility "
                            f"- {hba_utility}, {key_error}")

        return True


    def run(self):
        """Run the sensor on its own thread."""

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(
                self.polling_interval, self._priority, self.run, ())
            return

        # Get scsi/fc hosts data
        self.hosts = self._hba.get_hosts()
        self.host_data = []
        for host in self.hosts:
            data = { host: self._hba.get_host_data(host) }
            if data:
                self.host_data.append(data)

        if not self.stored_hba_status:
            self.stored_hba_status = {"prev_hba_status": None}
            store.put(self.stored_hba_status, self.HBA_SENSOR_DATA)

        self._check_and_send_hba_status()
        self._check_and_send_hba_host_port_status()

        # Process until own message queue is empty
        while not self._is_my_msgQ_empty():
            json_msg, _ = self._read_my_msgQ()
            if json_msg is not None:
                self._process_msg(json_msg)

        # Schedule next run
        self._scheduler.enter(self.polling_interval, self._priority, self.run, ())


    def _process_msg(self, json_msg):
        """Process various messages sent to us on our msg queue"""

        if isinstance(json_msg, dict) is False:
            json_msg = json.loads(json_msg)

        self._log_debug(f"_processMsg, json_msg: {json_msg}")

        if json_msg.get("sensor_request_type") == "node_hba":

            # Parse UUID from request and send back in response if it's available
            _uuid =  "Not-Found"
            if json_msg.get("uuid") is not None:
                _uuid = json_msg.get("uuid")

            self._log_debug("_processMsg, sensor_request_type: "\
                    f"{json_msg.get('sensor_request_type')}, uuid: {_uuid}")

            resource_type = json_msg.get("node_request")
            if resource_type != self.HBA_RESOURCE_TYPE:
                return

            description = ""
            impact = ""
            recommendation = ""
            alert_type = "GET"
            hba_status = self.stored_hba_status.get("prev_hba_status")

            if hba_status == self.FRU_MISSING:
                alert_type = self.FRU_MISSING
                description = "HBA is missing"
                impact = self.impact()
                recommendation = "Please contact support team"

            elif hba_status == self.FRU_FAULT:
                for host in self.hosts:
                    port_status = self.stored_hba_status[host].get("prev_port_state")
                    if port_status != "running":
                        alert_type = self.FRU_FAULT
                        # Faulty port information will be available in message
                        description = "HBA port is not running"
                        impact = "HBA %s port_%s can not be monitored" % (
                            host, self.host_data[host]['port_id'])
                        recommendation = "Please contact support team"
                        break

            self._create_message(alert_type, resource_type, resource_id="*",
                                 _uuid=_uuid, description=description,
                                 impact=impact, recommendation=recommendation)

            self._notify_node_data_msg_handler()


    def _get_info(self, alert_type, resource_type, resource_id="*", fru=False,
                  description="", impact="", recommendation=""):
        """Create info required in the response."""

        info = {}
        info["resource_type"] = resource_type
        info["resource_id"] = resource_id
        info["fru"] = fru
        info["event_time"] = str(int(time.time()))
        info["description"] = description
        if alert_type in [self.FRU_FAULT, self.FRU_MISSING]:
            info["impact"] = impact
            info["recommendation"] = recommendation

        return info


    def _get_specific_info(self):
        """Create specific info required in the response."""

        specific_info = {}
        model, vendor = self._hba._get_model_vendor()
        specific_info["model"] = model
        specific_info["vendor"] = vendor
        specific_info["initiators_count"] = len(self.hosts)
        specific_info["initiators"] = self.host_data
        specific_info["host_type"] = self._hba.host_type

        return specific_info


    def _create_message(self, alert_type, resource_type, resource_id="*",
                        _uuid="", description="", impact="", recommendation=""):
        """Queues the message to NodeData Message Handler."""

        fru = True if resource_type == self.HBA_RESOURCE_TYPE else False
        epoch_time = str(int(time.time()))
        alert_id = self._get_alert_id(epoch_time)
        severity = SeverityReader().map_severity(alert_type.lower())
        info = self._get_info(alert_type, resource_type, resource_id, fru,
                              description, impact, recommendation)
        specific_info = self._get_specific_info()

        hba_data = HBADataMsg(OSUtils.get_fqdn(),
                              alert_type,
                              alert_id,
                              severity,
                              info=info,
                              specific_info=specific_info,
                              time=epoch_time)

        if _uuid:
            hba_data.set_uuid(_uuid)
        self.hba_data_msg = hba_data.getJson()


    def _notify_node_data_msg_handler(self):
        """Notify NodeDataMsgHandler to update sensor data dict."""

        if self.hba_data_msg:
            self._write_internal_msgQ(NodeDataMsgHandler.name(),
                                      self.hba_data_msg)


    def _check_and_send_hba_status(self):
        """
        Compare HBA card current status with previous status.

        If status mismatch found,
        1. Send fault alert if HBA card is removed
        2. Send fault_resolved alert if HBA card is inserted
        3. Update new status to persistent data
        """

        if not self._hba.detected and \
            self.stored_hba_status.get("prev_hba_status") != self.FRU_MISSING:
            # Send HBA card fault alert
            resource_id = "hba"
            resource_type = self.HBA_RESOURCE_TYPE
            alert_type = self.FRU_MISSING
            description = "HBA card is missing"
            recommendation = "Insert HBA card"
            self._create_message(alert_type, resource_type, resource_id,
                                 description=description,
                                 recommendation=recommendation,
                                 impact=self.impact())
            self._notify_node_data_msg_handler()
            # Update persistent cache
            self.stored_hba_status["prev_hba_status"] = self.FRU_MISSING
            store.put(self.stored_hba_status, self.HBA_SENSOR_DATA)

        elif self._hba.detected and \
            self.stored_hba_status.get("prev_hba_status") == self.FRU_MISSING:
            # Send HBA card fault_resolved alert
            resource_id = "hba"
            resource_type = self.HBA_RESOURCE_TYPE
            alert_type = self.FRU_INSERTION
            description = "HBA card is inserted"
            self._create_message(alert_type, resource_type, resource_id,
                                 description=description)
            self._notify_node_data_msg_handler()
            # Update persistent cache
            self.stored_hba_status["prev_hba_status"] = self.FRU_INSERTION
            store.put(self.stored_hba_status, self.HBA_SENSOR_DATA)

        elif self._hba.detected and \
            self.stored_hba_status.get("prev_hba_status") == self.FRU_FAULT:
            for host in self.hosts:
                data = self._hba.get_host_data(host)
                if data["state"] != "running":
                    return

            # Send HBA card fault_resolved alert
            resource_id = "hba"
            resource_type = self.HBA_RESOURCE_TYPE
            alert_type = self.FRU_FAULT_RESOLVED
            description = "HBA card ports are running"
            self._create_message(alert_type, resource_type, resource_id,
                                 description=description)
            self._notify_node_data_msg_handler()
            # Update persistent cache
            self.stored_hba_status["prev_hba_status"] = self.FRU_FAULT_RESOLVED
            store.put(self.stored_hba_status, self.HBA_SENSOR_DATA)


    def _check_and_send_hba_host_port_status(self):
        """
        Compare HBA host port current status with previous status.

        If status mismatch found,
        1. Send fault alert if HBA host port is not running
        2. Send fault_resolved alert if HBA host port is running
        3. Update new status to persistent data
        """

        # If HBA card is not detected, ignore host port monitoring
        if not self._hba.detected:
            return

        for item in self.host_data:
            host = list(item.keys())[0]
            data = list(item.values())[0]

            if self.stored_hba_status.get(host) is None:
                self.stored_hba_status[host] = {
                        "prev_port_state": None
                    }

            prev_port_state = self.stored_hba_status[host].get("prev_port_state")

            if ( prev_port_state == "running" or not prev_port_state ) and \
                data["state"] !=  "running":
                # Raise fault alert on host port
                resource_id = f"{host}_{data['port_id']}"
                resource_type = self.HBA_RESOURCE_TYPE
                alert_type = self.FRU_FAULT
                description = f"{host} port status is not running"
                recommendation = "Please check %s port %s" % (host, data['port_id'])
                self._create_message(alert_type, resource_type, resource_id,
                                     description=description,
                                     recommendation=recommendation,
                                     impact="%s port is disabled" % host)
                self._notify_node_data_msg_handler()

                # Update persistent cache
                self.stored_hba_status["prev_hba_status"] = self.FRU_FAULT
                self.stored_hba_status[host]["prev_port_state"] = data["state"]
                store.put(self.stored_hba_status, self.HBA_SENSOR_DATA)

            elif prev_port_state and prev_port_state != "running" and \
                data["state"] ==  "running":
                # Raise fault_resolved alert on host port
                resource_id = f"{host}_{data['port_id']}"
                resource_type = self.HBA_RESOURCE_TYPE
                alert_type = self.FRU_FAULT_RESOLVED
                description = f"{host} port status is changed to running"
                self._create_message(alert_type, resource_type, resource_id,
                                     description=description)
                self._notify_node_data_msg_handler()

                # Update persistent cache
                self.stored_hba_status[host]["prev_port_state"] = data["state"]
                store.put(self.stored_hba_status, self.HBA_SENSOR_DATA)


    @staticmethod
    def _get_alert_id(epoch_time):
        """
        Returns alert id which is a combination of epoch_time and
        salt value.
        """

        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id


    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""

        super(HBASensor, self).suspend()
        self._suspended = True


    def resume(self):
        """Resumes the module thread. It should be non-blocking"""

        super(HBASensor, self).resume()
        self._suspended = False


    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""

        super(HBASensor, self).shutdown()
