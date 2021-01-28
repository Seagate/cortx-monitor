# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
Sensor Module Thread responsible for sensing SAS port/cable changes
on the Node server
"""

import errno
import json
import os
import socket
import time
import uuid

from framework.base.debug import Debug
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from framework.base.sspl_constants import DATA_PATH
from framework.utils.conf_utils import (CLUSTER, GLOBAL_CONF, SRVNODE,
                                        SSPL_CONF, Conf)
from framework.utils.config_reader import ConfigReader
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from framework.utils.store_factory import file_store
from framework.utils.sysfs_interface import SysFS
from framework.utils.tool_factory import ToolFactory
from message_handlers.logging_msg_handler import LoggingMsgHandler
from message_handlers.node_data_msg_handler import NodeDataMsgHandler

# Override default store
store = file_store

# Utility function used in sensor class
def sort_phy_list(phy_list):
    """Sorts phy list based on phy num."""
    # List to be returned
    sorted_list = []
    # Phy num to phy name mapping
    phy_num_dict = {}
    # List of phy nums
    num_list = []
    for phy in phy_list:
        # Read phy num eg phy-0:12 -> 12
        num = int(phy.split(':')[1])
        num_list.append(num)
        phy_num_dict[num] = phy
    # Sort the numbers
    num_list.sort()
    for num in num_list:
        sorted_list.append(phy_num_dict[num])
    return sorted_list

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
    CACHE_DIR_NAME  = "server"

    RESOURCE_ID = "SASHBA-0"
    DEFAULT_POLLING_INTERVAL = '30'

    PROBE = "probe"

    # Dependency list
    DEPENDENCIES = {
            "plugins": ["NodeDataMsgHandler", "LoggingMsgHandler"],
            "rpms": []
        }

    # Number of SAS Ports
    NUM_SAS_PORTS = 4
    # Number of Phys in a Port
    NUM_PHYS_PER_PORT = 4
    # Current Data Version
    CURRENT_DATA_VERSION = 1

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
        self.sas_ports_status = {}
        self.port_phy_list_dict = {}
        self.sas_phy_stored_alert = None

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(SASPortSensor, self).initialize(conf_reader)

        super(SASPortSensor, self).initialize_msgQ(msgQlist)

        self._site_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{self.SITE_ID}",'DC01')
        self._rack_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{self.RACK_ID}",'RC01')
        self._node_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{self.NODE_ID}",'SN01')
        self._cluster_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{self.CLUSTER_ID}",'CC01')

        # Get the sas port implementor from configuration
        sas_port_utility = Conf.get(SSPL_CONF, f"{self.name().capitalize()}>{self.PROBE}",
                                    "sysfs")

        self.polling_interval = int(Conf.get(SSPL_CONF, f"{self.SENSOR_NAME.upper()}>{self.POLLING_INTERVAL}",
                                        self.DEFAULT_POLLING_INTERVAL))

        # Creating the instance of ToolFactory class
        self.tool_factory = ToolFactory()

        cache_dir_path = os.path.join(DATA_PATH, self.CACHE_DIR_NAME)
        self.SAS_PORT_SENSOR_DATA = os.path.join(cache_dir_path, f'SAS_PORT_SENSOR_DATA_{self._node_id}')

        alert_type = None

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
                    phy_status = 'up'
                    # Increment global phy_link count for UP status
                    self.phy_link_count += 1
                else:
                    phy_status = 'fault'
                link_value_phy_status_collection = (value, phy_status)
                self.phy_dir_to_linkrate_mapping[phy] = link_value_phy_status_collection

            # Get the stored previous alert info
            self.sas_phy_stored_alert = store.get(self.SAS_PORT_SENSOR_DATA)
            self.check_and_send_alert()

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

    def update_sas_ports_status(self):
        """
        Reads current phy status and updates port connectivity status
        Assumption : phys will be present in multiples of 4
        """
        phy_list = [*self.phy_dir_to_linkrate_mapping]
        phy_list = sort_phy_list(phy_list)

        # Now we have a sorted list of phys
        # Phys 0-3 for the 0th sas port, and so on in groups of 4 phys
        # List containing status of all phys
        hba = []
        for phy in phy_list:
            if self.phy_dir_to_linkrate_mapping[phy][1] == 'up':
                hba.append(1)
            else:
                hba.append(0)

        for i in range(0,self.NUM_SAS_PORTS):
            # Save phy names forming this port for future use
            self.port_phy_list_dict[i] = phy_list[ self.NUM_PHYS_PER_PORT * i : \
                                                        self.NUM_PHYS_PER_PORT * i + self.NUM_PHYS_PER_PORT ]
            # Check port status
            s = set( hba[ self.NUM_PHYS_PER_PORT * i : self.NUM_PHYS_PER_PORT * i + self.NUM_PHYS_PER_PORT ])
            if len(s) == 1 and 0 in s:
                port_status = 'down'
            elif len(s) == 1 and 1 in s:
                port_status = 'up'
            else:
                port_status = 'degraded'
            # Store the data
            self.sas_ports_status[i] = port_status

    def check_and_send_conn_alert(self):
        """
        Sends conn fault alert if all phys go down
        Sends conn fault_resolved alert if at least 1 sas port (4 phys) comes up
        """
        # Case 1 : all fault for fault alert
        cur_all_fault = True

        # Case 2 : all fault_resolved for fault_resolved alert
        cur_all_fault_resolved = True

        # Previous conn alert that was sent
        prev_conn_alert = self.sas_phy_stored_alert['conn']

        # Current
        for port, value in self.sas_phy_stored_alert.items():
            if port in ['version','conn']:
                # This is key for conn alert, skip
                continue

            # Case 1 : All faults in current status
            if value != 'fault':
                cur_all_fault = False

            # Case 2 : All fault_resolved in current status
            elif value != 'fault_resolved':
                cur_all_fault_resolved = False

        if prev_conn_alert == 'fault_resolved' and cur_all_fault:
            # Send conn fault alert
            alert_type = 'fault'
            self._generate_alert(alert_type,-1)
            self.sas_phy_stored_alert['conn'] = alert_type

        elif prev_conn_alert == 'fault' and cur_all_fault_resolved:
            # Send conn fault_resolved alert
            alert_type = 'fault_resolved'
            self._generate_alert(alert_type,-1)
            self.sas_phy_stored_alert['conn'] = alert_type

    def handle_current_version_data(self):
        """Contains logic to check and send alert if data has version == 1."""
        # Compare current status of each port with previous alert_type
        for port, value in self.sas_phy_stored_alert.items():
            if port in ['version','conn']:
                # Skip
                continue
            if value == 'fault_resolved' and \
                        self.sas_ports_status[port] == 'down':
                alert_type = 'fault'
                self._generate_alert(alert_type, port)
                self.sas_phy_stored_alert[port] = alert_type
            elif value == 'fault' and \
                        self.sas_ports_status[port] == 'up':
                alert_type = 'fault_resolved'
                self._generate_alert(alert_type, port)
                self.sas_phy_stored_alert[port] = alert_type
        # See if conn failure/conn resolved alert needs to be sent
        self.check_and_send_conn_alert()
        # Save data to store
        store.put(self.sas_phy_stored_alert, self.SAS_PORT_SENSOR_DATA)

    def check_and_send_alert(self):
        """Checks whether conditions are met and sends alert if required
        Alerts will be sent if -
        1. All 4 phys of a sas port go up -> down : fault alert
        2. All 4 phys of a sas port come down -> up : fault_resolved alert
        Sensor data stored in persistent storage is a dict of { sas_port_number : alert_type }
        """
        # Update sas ports status
        self.update_sas_ports_status()

        # Check the version of stored alert
        version = None
        try:
            # Try to get the version
            # Exception will be raised if stored alert is None or no Version is available
            version = self.sas_phy_stored_alert['version']
        except Exception:
            logger.warning(f"Found no data or old data format for SASPortSensor, \
                            updating data format to version {self.CURRENT_DATA_VERSION}")
            # Versioning is not implemented or there is no data, write new data
            # Initialize dummy fault_resolved for all sas ports and conn
            self.sas_phy_stored_alert = {}
            self.sas_phy_stored_alert['version'] = self.CURRENT_DATA_VERSION
            self.sas_phy_stored_alert['conn'] = 'fault_resolved'
            for i in range(0,self.NUM_SAS_PORTS):
                self.sas_phy_stored_alert[i] = 'fault_resolved'
            # Save data to store
            store.put(self.sas_phy_stored_alert, self.SAS_PORT_SENSOR_DATA)

        if version == self.CURRENT_DATA_VERSION:
            self.handle_current_version_data()

    def run(self):
        """Run the sensor on its own thread"""

        alert_type = None
        status = None

        new_phy_up = 0
        new_phy_down = 0

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
                    # negotiated link rate
                    if link_rate.lower() != prev_linkrate_value.lower():
                        # If current link rate has no value like 12/6/3 Gbit
                        # and previously it was up, then it's a fault condition
                        if 'Gbit'.lower() not in link_rate.lower() and prev_alert_type.lower() == 'up':
                            # Increment count for new phy down which were up previously
                            new_phy_down +=1

                            # Make respective phy_status as fault
                            status = 'fault'

                        # Check if 12/6/3 Gbit is there in the current link rate and
                        # the previous alert_type is fault. If so, means phy is Up again
                        elif 'Gbit'.lower() in link_rate.lower() and prev_alert_type.lower() == 'fault':

                            # Mark respective phy_status as Up
                            status = 'up'

                            # Increment count for new phy up
                            new_phy_up +=1

                        # Finally update the global dict with current link rate
                        # and respctive phy status
                        self.phy_dir_to_linkrate_mapping[key] = (link_rate, status)

                # Get current phy status i.e number of Up phys
                new_phy_link_count = self.phy_link_count + new_phy_up - new_phy_down

                # Get the last sent alert info
                self.sas_phy_stored_alert = store.get(self.SAS_PORT_SENSOR_DATA)
                self.check_and_send_alert()
                # Update current active phy count for next iteration
                self.phy_link_count = new_phy_link_count

        except Exception as ae:
            logger.exception(ae)

        # Fire every 30 seconds to see if there's a change in the phy status
        self._scheduler.enter(self.polling_interval, self._priority, self.run, ())

    def _create_json_message(self, alert_type, port):
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

        if port != -1:
            # This is a port level alert, add an error key in specific info
            if alert_type == 'fault':
                specific_info["error"] = f"No connectivity detected on the SAS port {port}, possible \
causes could be missing SAS cable, bad cable connection, faulty cable or SAS port failure"
            elif alert_type == 'fault_resolved':
                specific_info["error"] = "null"
            specific_info_list.append(specific_info)
            specific_info = {}

        # specific_info will contain all 16 phys for conn level alert
        # Only 4 phys for port level alert
        for key, val in self.phy_dir_to_linkrate_mapping.items():
            if port != -1:
                # This is a port level alert, skip phys that are not relevant
                if key not in self.port_phy_list_dict[port]:
                    # Skip adding this phy
                    continue
            # Key will be phy-0:0. So, aplit it using ':'
            # So, structure will be SASHBA-0:phy-0
            phy_number = key.split(":")[1]
            specific_info["resource_id"] = self.RESOURCE_ID + ':' + "phy-" + phy_number
            specific_info["negotiated_link_rate"] = self.phy_dir_to_linkrate_mapping[key][0].strip()
            specific_info_list.append(specific_info)
            specific_info = {}

        alert_specific_info = specific_info_list

        if port == -1:
            # This is a SAS HBA level connection alert
            info = {
                    "site_id": self._site_id,
                    "cluster_id": self._cluster_id,
                    "rack_id": self._rack_id,
                    "node_id": self._node_id,
                    "resource_type": self.RESOURCE_TYPE, # node:interface:sas
                    "resource_id": self.RESOURCE_ID, # SASHBA-0
                    "event_time": epoch_time
                    }
        else:
            # This is a port level alert
            info = {
                    "site_id": self._site_id,
                    "cluster_id": self._cluster_id,
                    "rack_id": self._rack_id,
                    "node_id": self._node_id,
                    "resource_type": self.RESOURCE_TYPE + ':port', # node:interface:sas:port
                    "resource_id": self.RESOURCE_ID + f'-port-{port}', # SASHBA-0-port-0
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

    def _generate_alert(self, alert_type, port):
        """Queues the message to NodeData Message Handler"""

        json_msg = self._create_json_message(alert_type, port)
        if json_msg:
            # RAAL stands for - RAise ALert
            logger.info(f"RAAL: {json_msg}")
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
