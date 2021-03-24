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
  Description:       Monitors /proc/mdstat for changes and notifies
                    the node_data_msg_handler when a change is detected
 ****************************************************************************
"""
import json
import os
import socket
import subprocess
import time
import uuid

from zope.interface import implementer

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from framework.base.sspl_constants import COMMON_CONFIGS
from framework.utils.conf_utils import (CLUSTER, GLOBAL_CONF, SRVNODE,
                                        SSPL_CONF, Conf)
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from message_handlers.logging_msg_handler import LoggingMsgHandler
# Modules that receive messages from this module
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from sensors.Iraid import IRAIDsensor


@implementer(IRAIDsensor)
class RAIDsensor(SensorThread, InternalMsgQ):


    SENSOR_NAME       = "RAIDsensor"
    PRIORITY          = 1
    RESOURCE_TYPE     = "node:os:raid_data"

    # Section and keys in configuration file
    RAIDSENSOR        = SENSOR_NAME.upper()
    RAID_STATUS_FILE  = 'RAID_status_file'

    RAID_CONF_FILE    = '/etc/mdadm.conf'
    RAID_DOWN_DRIVE_STATUS = [ { "status" : "Down/Missing" }, { "status" : "Down/Missing" } ]

    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "site_id"
    CLUSTER_ID = "cluster_id"
    NODE_ID = "node_id"
    RACK_ID = "rack_id"

    prev_alert_type = {}
    alert_type = None

    # alerts
    FAULT_RESOLVED = "fault_resolved"
    FAULT = "fault"
    MISSING = "missing"
    INSERTION = "insertion"

    # Dependency list
    DEPENDENCIES = {
                    "init": ["DiskMonitor"],
    }

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RAIDsensor.SENSOR_NAME

    def __init__(self):
        super(RAIDsensor, self).__init__(self.SENSOR_NAME,
                                         self.PRIORITY)
        # Current RAID status information
        self._RAID_status = None

        # Location of hpi data directory populated by dcs-collector
        self._start_delay  = 10

        # Flag to indicate suspension of module
        self._suspended = False

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RAIDsensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RAIDsensor, self).initialize_msgQ(msgQlist)

        self._RAID_status_file = self._get_RAID_status_file()
        logger.info(f"Monitoring RAID status file: {self._RAID_status_file}")

        # The status file contents
        self._RAID_status_contents = "N/A"

        # The mdX status line in the status file
        self._RAID_status = {}

        self._faulty_drive_list = {}

        self._faulty_device_list = {}

        self._drives = {}

        self._total_drives = {}

        self._devices = []

        self._missing_drv = {}

        self._prev_drive_dict = {}

        self._site_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{self.SITE_ID}",'DC01')
        self._rack_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{self.RACK_ID}",'RC01')
        self._node_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{SRVNODE}>{self.NODE_ID}",'SN01')
        self._cluster_id = Conf.get(GLOBAL_CONF, f"{CLUSTER}>{self.CLUSTER_ID}",'CC01')
        # Allow systemd to process all the drives so we can map device name to serial numbers
        #time.sleep(120)

        return True

    def read_data(self):
        """Return the Current RAID status information"""
        return self._RAID_status

    def run(self):
        """Run the sensor on its own thread"""

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(30, self._priority, self.run, ())
            return


        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        # self._set_debug(True)
        # self._set_debug_persist(True)

        try:
            # Check for a change in status file and notify the node data msg handler
            self._notify_NodeDataMsgHandler()
        except Exception as ae:
            logger.exception(ae)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 30 seconds to see if there's a change in RAID status file
        self._scheduler.enter(30, self._priority, self.run, ())

    def _notify_NodeDataMsgHandler(self):
        """See if the status files changed and notify node data message handler
            for generating JSON message"""
        self._drive_state_changed = False
        # resource_id for drive alerts
        resource_id = None
        if not os.path.isfile(self._RAID_status_file):
            logger.warn(f"status_file: {self._RAID_status_file} does not exist, ignoring.")
            return

        # Read in status and see if it has changed
        with open(self._RAID_status_file, "r") as datafile:
            status = datafile.read()

        # Do nothing if the RAID status file has not changed
        if self._RAID_status_contents == status:
            self._log_debug(f"_notify_NodeDataMsgHandler status unchanged, ignoring: {status}")
            return

        # Update the RAID status contents of file
        self._RAID_status_contents = status

        # Process mdstat file and send json msg to NodeDataMsgHandler
        md_device_list, drive_dict, drive_status_changed = self._process_mdstat()

        # checks mdadm conf file for missing raid array and send json message to NodeDataMsgHandler
        self._process_missing_md_devices(md_device_list, drive_dict)

        for device in md_device_list:
            if drive_dict:
                if len(drive_dict[device]) < self._total_drives[device] and \
                    device in self.prev_alert_type and self.prev_alert_type[device] != self.MISSING:
                    self.alert_type = self.MISSING
                    if device in self._prev_drive_dict:
                        missing_drive = set(self._prev_drive_dict[device]).difference(set(drive_dict[device]))
                        try:
                            missing_drive = "/dev/"+list(missing_drive)[0]
                        except IndexError:
                            missing_drive = "NA"
                    else:
                        missing_drive = "NA"
                    resource_id = device+":"+missing_drive
                    self._missing_drv = {"path": missing_drive, "serialNumber": "None"}
                    self._map_drive_status(device, drive_dict, "Missing")
                    self._drive_state_changed = True

                elif len(drive_dict[device]) >= self._total_drives[device] and \
                    device in self.prev_alert_type and self.prev_alert_type[device] == self.MISSING:
                    self.alert_type = self.INSERTION
                    resource_id = device+":/dev/"+drive_dict[device][0]
                    self._map_drive_status(device, drive_dict[device][0], "Down/Recovery")
                    self._drive_state_changed = True

                if self.alert_type is not None and self._drive_state_changed == True:
                    self._prev_drive_dict[device] = drive_dict[device]
                    self._send_json_msg(self.alert_type, resource_id, device, self._drives[device])

                if drive_status_changed[device]:
                    for drive in self._drives[device]:
                        if drive.get("identity") is not None:
                            drive_path = drive.get("identity").get("path")
                            drive_name = drive_path[5:]
                            resource_id = device+":/dev/"+drive_name
                            drive_status = drive.get("status")
                            if drive_status not in ["U", "UP"] and device in self._faulty_drive_list and \
                                drive_name not in self._faulty_drive_list[device] and \
                                self.prev_alert_type[device] != self.MISSING:
                                self.alert_type = self.FAULT
                                self._map_drive_status(device, drive_name, "Down")
                                self._drive_state_changed = True
                                self._faulty_drive_list[device][drive_name] = self.alert_type

                            elif drive_status in ["U", "UP", "Down/Recovery"] and device in self._faulty_drive_list and \
                                drive_name in self._faulty_drive_list[device]:
                                self.alert_type = self.FAULT_RESOLVED
                                self._map_drive_status(device, drive_name, "UP")
                                self._drive_state_changed = True
                                del self._faulty_drive_list[device][drive_name]

                            if self.alert_type is not None and self._drive_state_changed == True:
                                self._prev_drive_dict[device] = drive_dict[device]
                                self._send_json_msg(self.alert_type, resource_id, device, self._drives[device])

    def _process_mdstat(self):
        """Parse out status' and path info for each drive"""
        # Replace new line chars with spaces
        mdstat = self._RAID_status_contents.strip().split("\n")
        md_device_list = []
        drive_dict = {}
        monitored_device = mdstat
        drive_status_changed = {}
        # Array of optional identity json sections for drives in array
        self._identity = {}

        # Read in each line looking for a 'mdXXX' value
        md_line_parsed = False

        for line in monitored_device:
            # The line following the mdXXX : ... contains the [UU] status that we need
            if md_line_parsed is True:
                # Format is [x/y][UUUU____...]
                drive_status_changed[self._device] = self._parse_raid_status(line, self._device)
                # Reset in case their are multiple configs in file
                md_line_parsed = False

            # Break the  line apart into separate fields
            fields = line.split(" ")

            # Parse out status' and path info for each drive
            if "md" in fields[0]:
                self._device = f"/dev/{fields[0]}"
                self._devices.append(self._device)
                self._log_debug(f"md device found: {self._device}")
                md_device_list.append(self._device)
                drive_dict[self._device] = []
                if self._device not in self.prev_alert_type:
                    self.prev_alert_type[self._device] = None
                if self._device not in self._faulty_drive_list:
                    self._faulty_drive_list[self._device] = {}

                # Parse out raid drive paths if they're present
                self._identity[self._device] = {}
                for field in fields:
                    if "[" in field:
                        if field not in drive_dict[self._device]:
                            index = field.find("[")
                            drive_name = field[:index]
                            drive_dict[self._device].append(drive_name)
                        self._add_drive(field, self._device)
                md_line_parsed = True

        return md_device_list, drive_dict, drive_status_changed

    def _add_drive(self, field, device):
        """Adds a drive to the list"""
        first_bracket_index = field.find('[')

        # Parse out the drive path
        drive_path = f"/dev/{field[: first_bracket_index]}"

        # Parse out the drive index into [UU] status which is Device Role field
        detail_command = f"/usr/sbin/mdadm --examine {drive_path} | grep 'Device Role'"
        response, error = self._run_command(detail_command)

        if error:
            self._log_debug(f"_add_drive, Error retrieving drive index into status, example: [U_]: {str(error)}")
        try:
            drive_index = int(response.split(" ")[-1])
        except Exception as ae:
            self._log_debug(f"_add_drive, get drive_index error: {str(ae)}")
            return
        self._log_debug(f"_add_drive, drive index: {drive_index}, path: {drive_path}")

        # Create the json msg, serial number will be filled in by NodeDataMsgHandler
        identity_data = {
                        "path" : drive_path,
                        "serialNumber" : "None"
                        }
        self._identity[device][drive_index] = identity_data

    def _parse_raid_status(self, status_line, device):
        """Parses the status of each drive denoted by U & _
            for drive being Up or Down in raid
        """
        # Parse out x for total number of drives
        first_bracket_index = status_line.find('[')

        # If no '[' found, return
        if first_bracket_index == -1:
            return False

        self._total_drives[device] = int(status_line[first_bracket_index + 1])
        self._log_debug("_parse_raid_status, total_drives: %d" % self._total_drives[device])

        # Break the line apart into separate fields
        fields = status_line.split(" ")

        # The last field is the list of U & _
        status = fields[-1]
        self._log_debug("_parse_raid_status, status: %s, total drives: %d" %
                        (status, self._total_drives[device]))

        # Array of raid drives in json format based on schema
        self._drives[device] = []

        drive_index = 0
        while drive_index < self._total_drives[device]:
            # Create the json msg and append it to the list
            if self._identity.get(device).get(drive_index) is not None:
                path = self._identity.get(device).get(drive_index).get("path")
                drive_status_msg = {
                                 "status" : status[drive_index + 1],  # Move past '['
                                 "identity": {
                                    "path": path,
                                    "serialNumber": "None"
                                    }
                                }
            else:
               drive_status_msg = {"status" : status[drive_index + 1]}  # Move past '['

            self._log_debug(f"_parse_raid_status, drive_index: {drive_index}")
            self._log_debug(f"_parse_raid_status, drive_status_msg: {drive_status_msg}")
            self._drives[device].append(drive_status_msg)

            drive_index = drive_index + 1

        # See if the status line has changed, if not there's nothing to do
        if device in self._RAID_status and self._RAID_status[device] == status:
            self._log_debug(f"RAID status has not changed, ignoring: {status}")
            return False
        else:
            self._log_debug(f"RAID status has changed, old: {self._RAID_status}, new: {status}")
            self._RAID_status[device] = status

        return True

    def _process_missing_md_devices(self, md_device_list, drive_dict):
        """ checks the md raid configuration file, compares all it's
            entries with list of arrays from mdstat file and sends
            missing entry in RabbitMQ channel
        """

        if not os.path.isfile(self.RAID_CONF_FILE):
            logger.warn(f"_process_missing_md_devices, MDRaid configuration file {self.RAID_CONF_FILE} is missing")
            return

        conf_device_list = []
        with open(self.RAID_CONF_FILE, 'r') as raid_conf_file:
            raid_conf_data = raid_conf_file.read().strip().split("\n")
        for line in raid_conf_data:
            try:
                raid_conf_field = line.split(" ")
                if "#" not in raid_conf_field[0] and "ARRAY" in raid_conf_field[0] and \
                    "/md" in raid_conf_field[1]:
                    # Mapped the device i.e. /dev/md/1 and /dev/md1 will be the same device.
                    map_device = raid_conf_field[1].split('md/')
                    if len(map_device)>1:
                        conf_device_list.append(map_device[0]+'md'+map_device[1])
                    else:
                        conf_device_list.append(raid_conf_field[1])
            except Exception as ae:
                self._log_debug(f"_process_missing_md_devices, error retrieving raid entry    \
                 from {self.RAID_CONF_FILE} file: {str(ae)}")
                return

        # compare conf file raid array list with mdstat raid array list
        for device in conf_device_list:
            if device not in md_device_list and device not in self._faulty_device_list:
                # add that missing raid array entry into the list of raid devices
                self.alert_type = self.FAULT
                self._send_json_msg(self.alert_type, device, device, self.RAID_DOWN_DRIVE_STATUS)
                self._faulty_device_list[device] = self.FAULT

            elif device in md_device_list and device in self._faulty_device_list:
                # add that missing raid array entry into the list of raid devices
                self.alert_type = self.FAULT_RESOLVED
                self._map_drive_status(device, drive_dict, "Down/Recovery")
                self._send_json_msg(self.alert_type, device, device, self._drives[device])
                del self._faulty_device_list[device]

    def _map_drive_status(self, device, drives, drv_status):
        for drv in self._drives[device]:
            if isinstance(drives, str):
                if drv["status"] not in ["U", "UP"] and drv["identity"]["path"] == '/dev/'+drives:
                    drv["status"] = drv_status
            else:
                for drive in drives[device]:
                    # Drive info is not available in missing case.
                    if drv_status == "Missing" and drv["status"] == "_":
                        drv["status"] = drv_status
                        drv["identity"] = self._missing_drv
                    elif drv["status"] not in ["U", "UP"] and drv["identity"]["path"] == '/dev/'+drive:
                        drv["status"] = drv_status

            if drv["status"] == "U":
                drv["status"] = "UP"

    def _send_json_msg(self, alert_type, resource_id, device, drives):
        """Transmit data to NodeDataMsgHandler to be processed and sent out"""

        epoch_time = str(int(time.time()))
        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        self._alert_id = self._get_alert_id(epoch_time)
        host_name = socket.getfqdn()

        if alert_type == self.MISSING:
            description = "RAID array or drive from RAID array is missing."
        elif alert_type == self.FAULT:
            description = "RAID array or drive from RAID array is faulty."
        elif alert_type == self.INSERTION:
            description = "Inserted drive in RAID array."
        elif alert_type == self.FAULT_RESOLVED:
            description = "Fault for RAID array or RAID drive is resolved"
        else:
            description = "Raid array alert"

        info = {
                "site_id": self._site_id,
                "cluster_id": self._cluster_id,
                "rack_id": self._rack_id,
                "node_id": self._node_id,
                "resource_type": self.RESOURCE_TYPE,
                "resource_id": resource_id,
                "event_time": epoch_time,
                "description": description
               }
        specific_info = {
            "device": device,
            "drives": drives
                }

        internal_json_msg = json.dumps(
            {"sensor_request_type" : {
                "node_data": {
                    "status": "update",
                    "sensor_type" : "node:os:raid_data",
                    "host_id": host_name,
                    "alert_type": alert_type,
                    "alert_id": self._alert_id,
                    "severity": severity,
                    "info": info,
                    "specific_info": specific_info
                    }
                }
            })
        self.prev_alert_type[device] = alert_type
        self.alert_type = None

        # Send the event to node data message handler to generate json message and send out
        self._write_internal_msgQ(NodeDataMsgHandler.name(), internal_json_msg)

    def _log_IEM(self):
        """Sends an IEM to logging msg handler"""
        json_data = json.dumps(
            {"sensor_request_type": {
                "node_data": {
                    "status": "update",
                    "sensor_type": "node:os:raid_data",
                    "device": self._devices,
                    "drives": self._drives
                    }
                }
            }, sort_keys=True)

        # Send the event to node data message handler to generate json message and send out
        internal_json_msg=json.dumps(
                {'actuator_request_type': {'logging': {'log_level': 'LOG_WARNING', 'log_type': 'IEM', 'log_msg': f'{json_data}'}}})

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
        epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id
    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RAIDsensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RAIDsensor, self).resume()
        self._suspended = False

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        self._log_debug(f"_run_command: {command}")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()

        if response:
            self._log_debug(f"_run_command, response: {str(response)}")
        if error:
            self._log_debug(f"_run_command: error: {str(error)}")

        return response.decode().rstrip('\n'), error.decode().rstrip('\n')

    def _get_RAID_status_file(self):
        """Retrieves the file containing the RAID status information"""
        return Conf.get(SSPL_CONF, f"{self.RAIDSENSOR}>{self.RAID_STATUS_FILE}",
                                                        '/proc/mdstat')
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RAIDsensor, self).shutdown()
