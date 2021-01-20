# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

"""
 ****************************************************************************
  Description:       Reads IEMs from RSyslog filtered file and sends
                    to RabbitMQ sensor channel.
  ****************************************************************************
"""
import errno
import select
import subprocess
import datetime
import os
import csv
import time
import threading

from framework.utils.conf_utils import *
from functools import lru_cache

from framework.base.module_thread import SensorThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.sspl_constants import iem_severity_types, iem_source_types, iem_severity_to_alert_mapping, COMMON_CONFIGS
from framework.utils.service_logging import logger
from framework.base.sspl_constants import PRODUCT_FAMILY

from json_msgs.messages.sensors.iem_data import IEMDataMsg
from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor


class IEMSensor(SensorThread, InternalMsgQ):
    """Monitors Rsyslog for IEMs"""

    SENSOR_NAME = "IEMSensor"
    SENSOR_RESP_TYPE = "iem_alert"
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"

    # Keys for config settings
    LOG_FILE_PATH_KEY = "log_file_path"
    TIMESTAMP_FILE_PATH_KEY = "timestamp_file_path"
    SITE_ID_KEY = "site_id"
    RACK_ID_KEY = "rack_id"
    NODE_ID_KEY = "node_id"
    CLUSTER_ID_KEY = "cluster_id"

    # Default values for config  settings
    DEFAULT_LOG_FILE_PATH = f"/var/log/{PRODUCT_FAMILY}/iem/iem_messages"
    DEFAULT_TIMESTAMP_FILE_PATH = f"/var/{PRODUCT_FAMILY}/sspl/data/iem/last_processed_msg_time"
    DEFAULT_SITE_ID = "001"
    DEFAULT_RACK_ID = "001"
    DEFAULT_NODE_ID = "001"
    DEFAULT_CLUSTER_ID= "001"

    # RANGE/VALID VALUES for IEC Components
    # NOTE: Ranges are   in hex number system.
    SEVERITY_LEVELS = ["A", "X", "E", "W", "N", "C", "I", "D", "B"]
    SOURCE_IDS = ["S", "H", "F", "O"]
    ID_MIN = "1"
    SITE_ID_MAX = "100"
    RACK_ID_MAX = "400"
    NODE_ID_MAX = "100"
    COMPONENT_ID_MAX = "100"
    MODULE_ID_MAX = "100"
    EVENT_ID_MAX = "2710"

    # Minimum length of IEC
    IEC_LENGTH = 12

    PRIORITY = 1
    IEC_KEYWORD = "IEC"

    IEC_MAPPING_DIR_PATH=f"/opt/seagate/{PRODUCT_FAMILY}/iem/iec_mapping"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["RabbitMQegressProcessor"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return IEMSensor.SENSOR_NAME

    @staticmethod
    def dependencies():
        """Returns a list of plugins and RPMs this module requires
           to function.
        """
        return IEMSensor.DEPENDENCIES

    def __init__(self):
        super(IEMSensor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)
        self._log_file_path = None
        self._timestamp_file_path = None
        self._site_id = None
        self._rack_id = None
        self._node_id = None
        self._cluster_id = None
        self._iem_logs = None
        self._iem_log_file_lock = threading.Lock()

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(IEMSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(IEMSensor, self).initialize_msgQ(msgQlist)

        # Read configurations

        self._log_file_path = Conf.get(SSPL_CONF, f"{self.SENSOR_NAME.upper()}>{self.LOG_FILE_PATH_KEY}",
                self.DEFAULT_LOG_FILE_PATH)

        self._timestamp_file_path = Conf.get(SSPL_CONF, f"{self.SENSOR_NAME.upper()}>{self.TIMESTAMP_FILE_PATH_KEY}",
                self.DEFAULT_TIMESTAMP_FILE_PATH)

        self._site_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{SITE_ID}",'001')
        self._rack_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{RACK_ID}",'001')
        self._node_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{NODE_ID}",'001')
        self._cluster_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{CLUSTER_ID}",'001')

        return True

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()
        try:
            with self._iem_log_file_lock:
                self._iem_logs = open(self._log_file_path)
            self._create_file(self._timestamp_file_path)

            with open(self._timestamp_file_path, "r") as timestamp_file:
                last_processed_log_timestamp = timestamp_file.read().strip()

            # Read and send unprocessed messages
            with self._iem_log_file_lock:
                for iem_log in self._iem_logs:
                    log = iem_log.rstrip()
                    log_timestamp = log[:log.index(" ")]
                    if not last_processed_log_timestamp or log_timestamp > last_processed_log_timestamp:
                        self._process_iem(log)

            # Reset debug mode if persistence is not enabled
            self._disable_debug_if_persist_false()

            # Read new messages
            self._read_iem()

        except IOError as io_error:
            if io_error.errno == errno.ENOENT:
                logger.debug(f"IEMSensor, self.run, {io_error.args} {io_error.filename}")
            elif io_error.errno == errno.EACCES:
                logger.error(f"IEMSensor, self.run, {io_error.args} {io_error.filename}")
            else:
                logger.error(f"IEMSensor, self.run, {io_error.args} {io_error.filename}")
            self._scheduler.enter(10, self._priority, self.run, ())
        except Exception as exception:
            logger.error(f"IEMSensor, self.run, {exception.args}")
            self._scheduler.enter(10, self._priority, self.run, ())

    def _read_iem(self):
        try:
            with self._iem_log_file_lock:
                for iem_log in self._iem_logs:
                    self._process_iem(iem_log.rstrip())
        except IOError as io_error:
            if io_error.errno == errno.ENOENT:
                logger.error(f"IEMSensor, self._read_iem, {io_error.args} {io_error.filename}")
            elif io_error.errno == errno.EACCES:
                logger.error(f"IEMSensor, self._read_iem, {io_error.args} {io_error.filename}")
            else:
                logger.error(f"IEMSensor, self._read_iem, {io_error.args} {io_error.filename}")
        except Exception as exception:
            logger.error(f"IEMSensor, self._read_iem, {exception.args}")
        finally:
            self._scheduler.enter(10, self._priority, self._read_iem, ())

    def _process_iem(self, iem_log):
        log_timestamp = iem_log[:iem_log.index(" ")]
        iem_msg = self._get_iem(iem_log)
        iem_components = self._extract_iem_components(iem_msg)
        if iem_components:
            logger.debug("IEM mesage {} {}".format(log_timestamp, iem_components))
            self._send_msg(iem_components, log_timestamp)
        with open(self._timestamp_file_path, "w") as timestamp_file:
            timestamp_file.write(log_timestamp)

    def _send_msg(self, iem_components, log_timestamp):
        """Creates JSON message from iem components and sends to RabbitMQ
           channel.
        """
        # IEM format is IEC:DESCRIPTION
        # IEC format is SEVERITY|SOURCEID|COMPONENTID|MODULEID|EVENTID
        # Field lengths ----1---|---1----|------3----|----3---|---4---
        # Example IEM -> "IEC: BO1001000001:Error in connecting to controller"
        # Actual IEC doesn't contain separator between fields. It is shown
        # here just for readability. Each field has fixed length.
        severity, source_id, component_id, module_id, event_id, description = \
                                                        [iem_components[i] for i in range(6)]

        # Check if severity level is valid
        if severity not in self.SEVERITY_LEVELS:
            logger.warn(f"Invalid Severity level: {severity}")
            return

        # Check for valid source id
        if source_id not in self.SOURCE_IDS:
            logger.warn(f"Invalid Source ID level: {source_id}")
            return

        # Check for valid event time
        event_time = self._get_epoch_time_from_timestamp(log_timestamp)
        if not event_time:
            logger.error("Timestamp is not in required format, discarding the message")
            return

        # Check for other components
        args = {
            "_comp_id": component_id,
            "_module_id": module_id,
            "_event_id": event_id
        }
        if not self._are_components_in_range(**args):
            return

        # Update severity and source_id
        alert_type = iem_severity_to_alert_mapping.get(severity)
        severity = iem_severity_types.get(severity, severity)
        source_id = iem_source_types.get(source_id, source_id)

        # Decode component_id, module_id and event_id
        component_id, module_id, event_id = self._decode_msg( f"{component_id}{module_id}{event_id}")

        info = {
            "site_id": self._site_id,
            "rack_id": self._rack_id,
            "node_id": self._node_id,
            "cluster_id" : self._cluster_id,
            "source_id": source_id,
            "component_id": component_id,
            "module_id": module_id,
            "event_id": event_id,
            "severity": severity,
            "description": description,
            "alert_type": alert_type,
            "event_time": event_time,
            "IEC": "".join(iem_components[:-1])
        }
        iem_data_msg = IEMDataMsg(info)
        json_msg = iem_data_msg.getJson()
        # RAAL stands for - RAise ALert
        logger.info(f"RAAL: {json_msg}")
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def _get_component(self, component):
        "Decode a component"
        if os.path.exists(f"{self.IEC_MAPPING_DIR_PATH}/components"):
            with open(f"{self.IEC_MAPPING_DIR_PATH}/components", newline='') as f:
                reader = csv.reader(f)
                for row in reader:
                    if component == row[0]:
                        return row[1]
                else:
                    return None
        else:
            return None


    @lru_cache(maxsize=32)
    def _decode_msg(self, code):
        "Decode a msg"

        component_id, module_id, event_id = code[:3], code[3:6], code[6:]
        component = self._get_component(component_id)
        if component:
            if os.path.exists(f"{self.IEC_MAPPING_DIR_PATH}/{component}"):
                with open(f"{self.IEC_MAPPING_DIR_PATH}/{component}", newline='') as f:
                    reader = csv.reader(f)
                    for row in reader:
                        if code == row[0]:
                            return component, row[1], row[2]
                    else:
                       return component, module_id, event_id
            else:
                return component, module_id, event_id
        else:
            return component_id, module_id, event_id

    def _get_iem(self, log):
        """Returns a string starting from the word <IEC> from a syslog
           log line.
        """
        if log is None or len(log.strip()) == 0:
            raise TypeError
        ret = None
        # IEM must contain a word IEC
        iec_keyword_index = log.find(self.IEC_KEYWORD)
        if iec_keyword_index != -1:
            ret = log[iec_keyword_index:]
        return ret

    def _are_components_in_range(self, _comp_id, _module_id, _event_id):
        """Validates various components of IEM against a predefined range.
            Returns True/False based on that check.
            TODO: Iterate directly over hex range instead of converting
                  it to int and then iterating.
        """
        components_in_range = True

        # Convert compoenents to int from hex string for comparison
        try:
            comp_id = int(_comp_id, 16)
            module_id = int(_module_id, 16)
            event_id = int(_event_id, 16)
        except ValueError as e:
            logger.warn(f"Invalide hex in iem messaage {e}")
            components_in_range = False
            return components_in_range

        # Check if component id out of range
        min_comp_id = int(self.ID_MIN, 16)
        max_comp_id = int(self.COMPONENT_ID_MAX, 16)
        if comp_id not in range(min_comp_id, max_comp_id + 1):
            logger.warn(f"Component Id {_comp_id} is not in range {self.ID_MIN}-{self.COMPONENT_ID_MAX}")
            components_in_range = False

        # Check if module id out of range
        min_mod_id = int(self.ID_MIN, 16)
        max_mod_id = int(self.MODULE_ID_MAX, 16)
        if module_id not in range(min_mod_id, max_mod_id + 1):
            logger.warn(f"Module Id {_module_id} is not in range {self.ID_MIN}-{self.MODULE_ID_MAX}")
            components_in_range = False

        # Check if event id out of range
        min_event_id = int(self.ID_MIN, 16)
        max_event_id = int(self.EVENT_ID_MAX, 16)
        if event_id not in range(min_event_id, max_event_id + 1):
            logger.warn(f"Event Id {_event_id} is not in range {self.ID_MIN}-{self.EVENT_ID_MAX}")
            components_in_range = False

        return components_in_range

    def _extract_iem_components(self, iem):
        """Splits iem in multiple components using a delimiter and
           return tuple of various extracted components.
        """
        components = []
        if iem is None or len(iem.strip()) == 0:
            raise TypeError
        things_to_strip = f"{self.IEC_KEYWORD}:"
        splitted_iem = iem[len(things_to_strip):].strip()
        # Split IEM by ":" delimieter. First part is IEC and second part
        # is description.
        iem_parts = splitted_iem.split(":")
        # Check for minimum length of IEC and presense of description
        if len(iem_parts) < 2 or len(iem_parts[0]) < self.IEC_LENGTH:
            logger.warn("Invalid IEM. Missing component")
            components = None
        else:
            components.append(iem_parts[0][0]) # Severity level
            components.append(iem_parts[0][1]) # Source ID
            components.append(iem_parts[0][2:5]) # Component ID
            components.append(iem_parts[0][5:8]) # Module ID
            components.append(iem_parts[0][8:]) # Event ID
            # if description is having ':'
            components.append(":".join(iem_parts[1:])) # Description level
        return components

    def _create_file(self, path):
        dir = path[:path.rindex("/")]
        if not os.path.exists(dir):
            os.makedirs(dir)
        if not os.path.exists(path):
            file = open(path, "w+")
            file.close()

    def _get_epoch_time_from_timestamp(self, timestamp):
        try:
            timestamp_format = '%Y-%m-%dT%H:%M:%S.%f%z'
            # Remove ":" from timezone. %z supports +0000. In timestamp it is +00:00
            timestamp = timestamp[:-3:] + timestamp[-2:]
            timestamp = time.strptime(timestamp, timestamp_format)
            return str(int(time.mktime(timestamp)))
        except ValueError:
            return None

    def refresh_file(self):
        if os.path.exists(self._log_file_path):
            with self._iem_log_file_lock:
                if self._iem_logs:
                    self._iem_logs.close()
                    self._iem_logs = open(self._log_file_path)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(IEMSensor, self).shutdown()
