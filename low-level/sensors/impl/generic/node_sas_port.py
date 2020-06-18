"""
Sensor Module Thread responsible for sensing SAS port/cable changes
on the Node server
"""

import errno
import json
import socket
import time
import uuid

from framework.utils.config_reader import ConfigReader
from framework.base.debug import Debug
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from message_handlers.logging_msg_handler import LoggingMsgHandler
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from framework.base.module_thread import SensorThread
from framework.utils.severity_reader import SeverityReader
from framework.utils.sysfs_interface import *
from framework.utils.tool_factory import ToolFactory
from framework.base.sspl_constants import COMMON_CONFIGS

class SASPortSensor(SensorThread, InternalMsgQ):
    """SAS Port Sensor which runs on its own thread periodically and
       is responsible for sensing changes is SAS ports/cable using
       available tool/utility"""

    SENSOR_NAME = "SASPortSensor"
    PRIORITY = 1
    RESOURCE_TYPE = "node:interface:sas"

    # section in the configuration store
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "site_id"
    CLUSTER_ID = "cluster_id"
    NODE_ID = "node_id"
    RACK_ID = "rack_id"
    POLLING_INTERVAL = "polling_interval"

    RESOURCE_ID = "SASHBA-0"
    DEFAULT_POLLING_INTERVAL = '30'

    PROBE = "probe"

    # Dependency list
    DEPENDENCIES = {
            "plugins": ["NodeDataMsgHandler", "LoggingMsgHandler"],
            "rpms": []

        }

    @staticmethod
    def name():
        """@return: name of the module."""
        return SASPortSensor.SENSOR_NAME

    def __init__(self, utility_instance=None):
        """init method"""
        super(SASPortSensor, self).__init__(self.SENSOR_NAME,
                                         self.PRIORITY)

        # Initialize the utility instance
        self._utility_instance = utility_instance

        self.phy_dir_to_linkrate_mapping = None

        # Flag to indicate suspension of module
        self._suspended = False
        self._count = 0
        self.phy_link_count = 0

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(SASPortSensor, self).initialize(conf_reader)

        super(SASPortSensor, self).initialize_msgQ(msgQlist)

        self._site_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.SITE_ID), '001')
        self._cluster_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.CLUSTER_ID), '001')
        self._rack_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.RACK_ID), '001')
        self._node_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.NODE_ID), '001')

        # get the sas port implementor from configuration
        sas_port_utility = self._conf_reader._get_value_with_default(
                                    self.name().capitalize(), self.PROBE,
                                    "sysfs")

        self.polling_interval = int(self._conf_reader._get_value_with_default(
            self.SENSOR_NAME.upper(), self.POLLING_INTERVAL, self.DEFAULT_POLLING_INTERVAL))

        # Creating the instance of ToolFactory class
        self.tool_factory = ToolFactory()

        try:
            # Get the instance of the utility using ToolFactory
            self._utility_instance = self._utility_instance or \
                                self.tool_factory.get_instance(sas_port_utility)
            self._utility_instance.initialize()
            phy_status = None

            link_value_phy_status_collection = ()

            # Call to sas phy dirctory which will return a dictionary
            # which has phy_name to negotiated link rate mapping
            # Ex: {"phy-0:0": "<12.0, Unknown>"}
            self.phy_dir_to_linkrate_mapping = \
                    self._utility_instance.get_phy_negotiated_link_rate()

            # Iterate over populated dictionary and restructure it
            # Ex: if phy-0:0 is 12.0/6.0/3.0, considered as UP.
            # {"phy-0:0": ("link_rate", <Up/Down>)}
            for phy, value in self.phy_dir_to_linkrate_mapping.items():
                if 'Gbit'.lower() in value.strip().lower():
                    phy_status = 'Up'
                    # Increment global phy_link count for UP status
                    self.phy_link_count += 1
                else:
                    phy_status = 'Down'
                link_value_phy_status_collection = (value, phy_status)
                self.phy_dir_to_linkrate_mapping[phy] = link_value_phy_status_collection
        except KeyError as key_error:
            logger.error(
                "Unable to get the instance of {} \
                Utility. Hence shutting down the sensor".format(sas_port_utility))
            self.shutdown()
        except Exception as e:
            if e == errno.ENOENT:
                logger.error(
                    "Problem occured while reading from sas_phy \
                    directory. directory path doesn't directory. Hence \
                    shuting down the sensor")
            elif e == errno.EACCES:
                logger.error(
                    "Problem occured while reading from sas_phy directory. \
                     Not enough permission to read from the directory. \
                     Hence shuting down the sensor")
            else:
                logger.error(
                    "Problem occured while reading from sas_phy directory. \
                     {0}. Hence shuting down the sensor".format(e))
            self.shutdown()

        return True

    def run(self):
        """Run the sensor on its own thread"""

        alert_type = None
        status = None

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(self.polling_interval, self._priority, self.run, ())
            return

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        try:
            phy_link_rate_dict = \
                self._utility_instance.get_phy_negotiated_link_rate()
            if phy_link_rate_dict:
                for key, value in phy_link_rate_dict.items():
                    link_rate = value.strip()
                    prev_linkrate_value = \
                        self.phy_dir_to_linkrate_mapping[key][0].strip()
                    prev_alert_type = \
                        self.phy_dir_to_linkrate_mapping[key][1].strip()
                    status = prev_alert_type

                    # Compare local dict wrt global dictionary for change in the
                    # negitiated link rate
                    if link_rate.lower() != prev_linkrate_value.lower():
                        # If current link rate has no value like 12/6/3 Gbit
                        # and previously it was up, then it's a fault condition
                        if 'Gbit'.lower() not in link_rate.lower() and prev_alert_type.lower() == 'up':
                            # Increase the phy count identified with fault
                            self._count += 1

                            # make respective phy_status as fault
                            status = 'fault'

                            # Compare with the phy count who were UP initially
                            if self._count == self.phy_link_count:
                                alert_type = 'fault'

                        # Check if 12/6/3 Gbit is there in the current link rate and
                        # the previous alert_type is fault. If so, means phy is Up again
                        elif 'Gbit'.lower() in link_rate.lower() and prev_alert_type.lower() == 'fault':

                            # Mark respective phy_status as Up
                            status = 'Up'

                            # Decrease the phy count identified with fault previously
                            self._count -= 1

                            # If all the phys are UP, fault_reolved case.
                            if self._count == 0:
                                alert_type = 'fault_resolved'

                        # Finally update the global dict with current link rate
                        # and respctive phy status
                        self.phy_dir_to_linkrate_mapping[key] = (link_rate, status)

                    # TODO: Needs to store the state in the consul
                    # In case node reboot happens
                    if alert_type:
                        self._generate_alert(alert_type)
                        alert_type = None
        except Exception as ae:
            logger.exception(ae)

        # Fire every 30 seconds to see if there's a change in the phy status
        self._scheduler.enter(self.polling_interval, self._priority, self.run, ())

    def _create_json_message(self, alert_type):
        """Creates a defined json message structure which can flow inside SSPL
           modules"""

        internal_json_msg = None
        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        epoch_time = str(int(time.time()))

        alert_id = self._get_alert_id(epoch_time)
        host_name = socket.gethostname()

        specific_info = {}
        specific_info_list = []

        for key, val in self.phy_dir_to_linkrate_mapping.items():
            # key will be phy-0:0. So, aplit it using ':'
            # So, structure will be SASHBA-0:phy-0
            phy_number = key.split(":")[1]
            specific_info["resource_id"] = self.RESOURCE_ID + ':' + "phy-" + phy_number
            specific_info["negotiated_link_rate"] = self.phy_dir_to_linkrate_mapping[key][0].strip()
            specific_info_list.append(specific_info)
            specific_info = {}

        alert_specific_info = specific_info_list

        info = {
                "site_id": self._site_id,
                "cluster_id": self._cluster_id,
                "rack_id": self._rack_id,
                "node_id": self._node_id,
                "resource_type": self.RESOURCE_TYPE,
                "resource_id": self.RESOURCE_ID,
                "event_time": epoch_time
                }

        internal_json_msg = json.dumps(
            {"sensor_request_type": {
                "node_data": {
                        "status": "update",
                        "host_id": host_name,
                        "alert_type": alert_type,
                        "severity": severity,
                        "alert_id": alert_id,
                        "info": info,
                        "specific_info": alert_specific_info
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

    def _generate_alert(self, alert_type):
        """Queues the message to NodeData Message Handler"""

        json_msg = self._create_json_message(alert_type)
        if json_msg:
            self._write_internal_msgQ(NodeDataMsgHandler.name(), json_msg)

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(SASPortSensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(SASPortSensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(SASPortSensor, self).shutdown()

