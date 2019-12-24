"""
 ****************************************************************************
 Filename:          iem_sensor.py
 Description:       Reads IEMs from Rsyslog through named pipe configured
                    in SSPL config file and sends them to RabbitMQ sensor
                    channel.
 Creation Date:     08/26/2019
 Author:            Malhar Vora

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by
 Seagate Technology, LLC.
 ****************************************************************************
"""
import errno
import select
import subprocess
import time
import datetime
import os

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

from json_msgs.messages.sensors.iem_data import IEMDataMsg
from rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor


class IEMSensor(ScheduledModuleThread, InternalMsgQ):
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

    # Default values for config  settings
    DEFAULT_LOG_FILE_PATH = "/var/sspl/data/iem/iem_messages"
    DEFAULT_TIMESTAMP_FILE_PATH = "/var/sspl/data/iem/last_processed_msg_time"
    DEFAULT_SITE_ID = "001"
    DEFAULT_RACK_ID = "001"
    DEFAULT_NODE_ID = "001"

    # RANGE/VALID VALUES for IEC Components
    # NOTE: Ranges are in hex number system.
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

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(IEMSensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(IEMSensor, self).initialize_msgQ(msgQlist)

        # Read configurations
        self._log_file_path = self._conf_reader._get_value_with_default(
            self.SENSOR_NAME.upper(), self.LOG_FILE_PATH_KEY,
            self.DEFAULT_LOG_FILE_PATH)

        self._timestamp_file_path = self._conf_reader._get_value_with_default(
            self.SENSOR_NAME.upper(), self.TIMESTAMP_FILE_PATH_KEY,
            self.DEFAULT_TIMESTAMP_FILE_PATH)

        self._site_id = self._conf_reader._get_value_with_default(
            self.SYSTEM_INFORMATION.upper(), self.SITE_ID_KEY, self.DEFAULT_SITE_ID)

        self._rack_id = self._conf_reader._get_value_with_default(
            self.SYSTEM_INFORMATION.upper(), self.RACK_ID_KEY, self.DEFAULT_RACK_ID)

        self._node_id = self._conf_reader._get_value_with_default(
            self.SYSTEM_INFORMATION.upper(), self.NODE_ID_KEY, self.DEFAULT_NODE_ID)

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()
        iem_components = None
        try:
            self._create_file(self._timestamp_file_path)
            f = subprocess.Popen(['tail','-Fn+1', self._log_file_path],\
            stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            p = select.poll()
            p.register(f.stdout)

            logger.info("Opened file to read IEM: {0}".format(self._log_file_path))
            while True:
                iem_components = iem_msg = None
                if p.poll():
                    data = f.stdout.readline().rstrip()
                    self._log_debug("Received line {0}".format(data[5:]))
                    if data:
                        log_timestamp = data[:data.index(" ")]
                        last_processed_log_timestamp = datetime.datetime.now().isoformat()
                        timestamp_file = open(self._timestamp_file_path, "r")
                        last_processed_log_timestamp = timestamp_file.read().strip()
                        timestamp_file.close()
                        if not last_processed_log_timestamp or log_timestamp > last_processed_log_timestamp:
                            iem_msg = self._get_iem(data)
                            iem_components = self._extract_iem_components(
                                iem_msg)
                            if iem_components:
                                logger.info("IEM mesage {} {}".format(log_timestamp, iem_components))
                                self._send_msg(iem_components)
                                timestamp_file = open(self._timestamp_file_path, "w")
                                timestamp_file.write(log_timestamp)
                                timestamp_file.close()


        except IOError as io_error:
            if io_error.errno == errno.ENOENT:
                logger.error(
                    "Unable to read IEM timestamp from file. "
                    "File doesn't exist: {0}".format(self._log_file_path))
            elif io_error.errno == errno.EACCES:
                logger.error(
                    "Unable to read IEM timestamp from file. "
                    "Permission denied while reading from: {0}".format(
                        self._log_file_path))
            else:
                logger.error(
                    "Unable to read IEM timestamp from file. "
                    "Error while reading from {0}:{1}".format(
                        self._log_file_path, str(io_error)))
        except ValueError as value_error:
            error_msg = value_error.message.split(":")[1].strip()
            logger.error("Invalid hex value: {0}".format(error_msg))

        except IndexError as index_error:
            # One major reason we get this error is some component is missing
            # in IEM so splitting an IEM using ":" faces and issue.
            logger.error("Missing component in IEM")

        except Exception as exception:
            logger.error(
                "Unable to read IEM timestamp from file. "
                "Error while reading from {0}:{1}".format(
                    self._log_file_path, str(exception)))
            logger.exception(exception)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 10 seconds
        logger.info("Retrying after 10 seconds...")
        self._scheduler.enter(10, self._priority, self.run, ())

    def _send_msg(self, iem_components):
        """Creates JSON message from iem components and sends to RabbitMQ
           channel.
        """
        # IEM format is IEC:DESCRIPTION
        # IEC format is SEVERITY|SOURCEID|COMPONENTID|MODULEID|EVENTID
        # Field lengths ----1---|---1----|------3----|----3---|---4---
        # Example IEM -> "IEC: BO1001000001:Error in connecting to controller"
        # Actual IEC doesn't contain separator between fields. It is shown
        # here just for readability. Each field has fixed length.
        severity = iem_components[0]
        source_id = iem_components[1]
        component_id = iem_components[2]
        module_id = iem_components[3]
        event_id = iem_components[4]
        description = iem_components[5]

        # Check if severity level is valid
        if severity not in self.SEVERITY_LEVELS:
            logger.warn("Invalid Severity level: {0}".format(severity))
            return

        # Check for valid source id
        if source_id not in self.SOURCE_IDS:
            logger.warn("Invalid Source ID level: {0}".format(source_id))
            return

        # Check for other components
        args = {
            "_site_id": self._site_id,
            "_rack_id": self._rack_id,
            "_node_id": self._node_id,
            "_comp_id": component_id,
            "_module_id": module_id,
            "_event_id": event_id
        }
        if not self._are_components_in_range(**args):
            return

        info = {
            "site_id": self._site_id,
            "rack_id": self._rack_id,
            "node_id": self._node_id,
            "source_id": source_id,
            "component_id": component_id,
            "module_id": module_id,
            "event_id": event_id,
            "severity": severity,
            "description": description
        }
        iem_data_msg = IEMDataMsg(info)
        json_msg = iem_data_msg.getJson()
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

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

    def _are_components_in_range(
        self, _site_id, _rack_id, _node_id, _comp_id, _module_id, _event_id):
        """Validates various components of IEM against a predefined range.
            Returns True/False based on that check.
            TODO: Iterate directly over hex range instead of converting
                  it to int and then iterating.
        """
        components_in_range = True

        # Convert compoenents to int from hex string for comparison
        site_id = int(_site_id, 16)
        rack_id = int(_rack_id, 16)
        node_id = int(_node_id, 16)
        comp_id = int(_comp_id, 16)
        module_id = int(_module_id, 16)
        event_id = int(_event_id, 16)

        # Check if site id out of range
        min_site_id = int(self.ID_MIN, 16)
        max_site_id = int(self.SITE_ID_MAX, 16)
        if site_id not in range(min_site_id, max_site_id + 1):
            logger.warn("Site Id {0} is not in range {1}-{2}".format(_site_id, self.ID_MIN, self.SITE_ID_MAX))
            components_in_range = False

        # Check if rack id out of range
        min_rack_id = int(self.ID_MIN, 16)
        max_rack_id = int(self.RACK_ID_MAX, 16)
        if rack_id not in range(min_rack_id, max_rack_id + 1):
            logger.warn("Rack Id {0} is not in range {1}-{2}".format(_rack_id, self.ID_MIN , self.RACK_ID_MAX))
            components_in_range = False

        # Check if node id out of range
        min_node_id = int(self.ID_MIN, 16)
        max_node_id = int(self.NODE_ID_MAX, 16)
        if node_id not in range(min_node_id, max_node_id + 1):
            logger.warn("Node Id {0} is not in range {1}-{2}".format(_node_id, self.ID_MIN, self.NODE_ID_MAX))
            components_in_range = False

        # Check if component id out of range
        min_comp_id = int(self.ID_MIN, 16)
        max_comp_id = int(self.COMPONENT_ID_MAX, 16)
        if comp_id not in range(min_comp_id, max_comp_id + 1):
            logger.warn("Component Id {0} is not in range {1}-{2}".format(_comp_id, self.ID_MIN, self.COMPONENT_ID_MAX))
            components_in_range = False

        # Check if module id out of range
        min_mod_id = int(self.ID_MIN, 16)
        max_mod_id = int(self.MODULE_ID_MAX, 16)
        if module_id not in range(min_mod_id, max_mod_id + 1):
            logger.warn("Module Id {0} is not in range {1}-{2}".format(_module_id, self.ID_MIN, self.MODULE_ID_MAX))
            components_in_range = False

        # Check if event id out of range
        min_event_id = int(self.ID_MIN, 16)
        max_event_id = int(self.EVENT_ID_MAX, 16)
        if event_id not in range(min_event_id, max_event_id + 1):
            logger.warn("Event Id {0} is not in range {1}-{2}".format(_event_id, self.ID_MIN, self.EVENT_ID_MAX))
            components_in_range = False

        return components_in_range

    def _extract_iem_components(self, iem):
        """Splits iem in multiple components using a delimiter and
           return tuple of various extracted components.
        """
        components = []
        if iem is None or len(iem.strip()) == 0:
            raise TypeError
        things_to_strip = "{0}:".format(self.IEC_KEYWORD)
        splitted_iem = iem.lstrip(things_to_strip).strip()
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
            components.append(iem_parts[1]) # Description level
        return components

    def _get_iem(self, log):
        """Returns a string starting from the word <IEC> from a syslog
           log line.
        """
        if log is None or len(log.strip()) == 0:
            raise TypeError
        ret = None
        iec_keyword_index = log.find(self.IEC_KEYWORD)
        if iec_keyword_index != -1:
            ret = log[iec_keyword_index:]
        return ret

    def _create_file(self, path):
        dir = path[:path.rindex("/")]
        if not os.path.exists(dir):
            os.makedirs(dir)
        if not os.path.exists(path):
            file = open(path, "w+")
            file.close()

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(IEMSensor, self).shutdown()
