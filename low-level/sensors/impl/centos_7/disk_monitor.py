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

  Description:Detects drive add/remove event,
              performs SMART on drives and notifies DiskMsgHandler.

 ****************************************************************************
"""
import copy
import json
import os
import re
import subprocess
import threading
import time
import uuid
from datetime import datetime, timedelta

import dbus
from dbus import Array, Interface, SystemBus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject as gobject
from zope.interface import implementer

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from framework.base.sspl_constants import cs_products
from framework.messaging.egress_processor import \
    EgressProcessor
from framework.utils.conf_utils import DATA_PATH_KEY, SSPL_CONF, Conf
from cortx.utils.log import Log as logger
from framework.utils.severity_reader import SeverityReader
from framework.utils.store_factory import file_store
from json_msgs.messages.actuators.ack_response import AckResponseMsg
from message_handlers.disk_msg_handler import DiskMsgHandler
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from sensors.ISystem_monitor import ISystemMonitor
from framework.utils.mon_utils import MonUtils
from framework.utils.iem import Iem
from framework.utils.os_utils import OSUtils
store = file_store

@implementer(ISystemMonitor)
class DiskMonitor(SensorThread, InternalMsgQ):


    SENSOR_NAME       = "DiskMonitor"
    PRIORITY          = 2

    # Section and keys in configuration file
    DISKMONITOR        = SENSOR_NAME.upper()
    SMART_TEST_INTERVAL= 'smart_test_interval'
    SMART_ON_START     = 'run_smart_on_start'
    SYSTEM_INFORMATION = 'SYSTEM_INFORMATION'
    SETUP              = 'setup'

    DEFAULT_RAS_VOL = "/var/cortx/sspl/data/"

    DISK_INSERTED_ALERT_TYPE = "insertion"
    DISK_REMOVED_ALERT_TYPE = "missing"

    # SMART test response
    SMART_STATUS_UNSUPPORTED = "Unsupported"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["DiskMsgHandler", "NodeDataMsgHandler"],
                    "init": ["HPIMonitor"],
                    "rpms": ["smartmontools"]
    }

    DISK_FAULT_ALERT_TYPE = "fault"
    DISK_FAULT_RESOLVED_ALERT_TYPE = "fault_resolved"
    DRIVE_DBUS_INFO = 'dbus_info'
    DRIVE_FAULT_ATTR = 'smart_attributes'
    NODE_DISK_RESOURCE_TYPE = "node:os:disk"
    ENCLOSURE_DISK_RESOURCE_TYPE = "enclosure:hw:disk"
    SMARTCTL_PASSED_RESPONSE = "SMART overall-health self-assessment test result: PASSED"
    UDISKS2_UNAVAILABLE = "org.freedesktop.UDisks2 was not provided"

    @staticmethod
    def name():
        """@return: name of the module."""
        return DiskMonitor.SENSOR_NAME

    def __init__(self):
        super(DiskMonitor, self).__init__(self.SENSOR_NAME,
                                                  self.PRIORITY)
        # Mapping of SMART jobs and their properties
        self._smart_jobs = {}

        # Mapping of SMART uuids from incoming requests so they can be used in the responses back to halon
        self._smart_uuids = {}

        # List of serial numbers which have been flagged for simulated failure of SMART tests from CLI
        self._simulated_smart_failures = []

        # Keep sleep 1 second to avoid delay for disk insertion/removal alerts
        self._thread_sleep = 1

        # Location of hpi data directory populated by dcs-collector
        self._hpi_base_dir = "/tmp/dcs/hpi"
        self._start_delay = 10



    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(DiskMonitor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(DiskMonitor, self).initialize_msgQ(msgQlist)

        # Retrieves the frequency to run SMART tests on all the drives
        self._smart_interval = self._getSMART_interval()

        self._run_smart_on_start = self._can_run_smart_on_start()
        self._log_debug(f"DiskMonitor, Run SMART test on start: {self._run_smart_on_start}")

        self._smart_supported = self._is_smart_supported()
        self._log_debug(f"DiskMonitor, SMART supported: {self._smart_supported}")

        # Dict of drives by-id symlink from systemd
        self._drive_by_id = {}

        # Dict of drives by-path symlink from systemd
        self._drive_by_path = {}

        # Dict of drives by device name from systemd
        self._drive_by_device_name = {}

        # Dict of drives by path
        self._drives = {}

        # Lock for the above two variables,
        # they will be concurrently accessed from both the _interface_added/_removed callbacks and
        # the run() function.
        self._drive_info_lock = threading.Lock()

        # Next time to run SMART tests
        self._next_smart_tm = datetime.now() + timedelta(seconds=self._smart_interval)

        # We need to speed up the thread to handle exp resets but then slow it back down to not chew up cpu
        self._thread_speed_safeguard = -1000  # Init to a negative number to allow extra time at startup

        self._product = product
        self._iem = Iem()
        self.os_utils = OSUtils()
        self._iem.check_existing_fault_iems()
        self.UDISKS2 = self._iem.EVENT_CODE["UDISKS2_UNAVAILABLE"][1]
        self.HDPARM = self._iem.EVENT_CODE["HDPARM_ERROR"][1]
        self.SMARTCTL = self._iem.EVENT_CODE["SMARTCTL_ERROR"][1]

        self.vol_ras = Conf.get(SSPL_CONF, f"{self.SYSTEM_INFORMATION}>{DATA_PATH_KEY}",
            self.DEFAULT_RAS_VOL)

        self.server_cache = self.vol_ras + "server/"
        self.disk_cache_path = self.server_cache + "systemd_watchdog/disks/disks.json"

        # Existing drives
        self._existing_drive = store.get(self.disk_cache_path)
        if self._existing_drive is None:
            self._existing_drive = {}
            store.put(self._existing_drive, self.disk_cache_path)


        # Integrate into the main dbus loop to catch events
        DBusGMainLoop(set_as_default=True)

        if self._product in cs_products:
            # Wait for the dcs-collector to populate the /tmp/dcs/hpi directory
            while not os.path.isdir(self._hpi_base_dir):
                logger.info(f"DiskMonitor, dir not found: {self._hpi_base_dir}")
                logger.info(f"DiskMonitor, rechecking in {self._start_delay} secs")
                time.sleep(int(self._start_delay))

        # Allow time for the hpi_monitor to come up
        #time.sleep(60)

        return True

    def read_data(self):
        """Return the dict of service status'"""
        return {}

    def run(self):
        """Run the monitoring periodically on its own thread."""

        #self._set_debug(True)
        #self._set_debug_persist(True)

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        self._log_debug("Start accepting requests")

        try:
            # Connect to dbus system wide
            self._bus = SystemBus()
            try:
                # Obtain a disk manager interface for monitoring drives
                disk_systemd = self._bus.get_object('org.freedesktop.UDisks2',
                    '/org/freedesktop/UDisks2')
                # these line executed only one time at start of sensor thread,
                # hence for udisks calling 'check_fault_resolved_iems()' function directly
                # instead of calling fault_resolved_iem().
                if self.UDISKS2 in self._iem.fault_iems:
                    self._iem.iem_fault_resolved("UDISKS2_AVAILABLE")
                    self._iem.fault_iems.remove(self.UDISKS2)
            except dbus.DBusException as err:
                logger.error("DiskMonitor: Error occurred while"
                    " initializing dbus UDisks interface. : %s" %err)
                if self.UDISKS2_UNAVAILABLE in str(err):
                    self._iem.iem_fault("UDISKS2_UNAVAILABLE")
                    if self.UDISKS2 not in self._iem.fault_iems:
                        self._iem.fault_iems.append(self.UDISKS2)
                    return

            self._disk_manager = Interface(disk_systemd,
                dbus_interface='org.freedesktop.DBus.ObjectManager')

            # Assign callbacks to all devices to capture signals
            self._disk_manager.connect_to_signal('InterfacesAdded', self._interface_added)
            self._disk_manager.connect_to_signal('InterfacesRemoved', self._interface_removed)

            # Notify DiskMsgHandler of available drives and schedule SMART tests
            self._init_drives()

            with self._drive_info_lock:
                # Prepare drives to monitor
                self._drives = self._get_drives()
                # send msg for new drives
                for drive_path in self._drives.keys():
                    if drive_path not in self._existing_drive:
                        drive = self._drives[drive_path][self.DRIVE_DBUS_INFO]
                        resource_type = self._get_resource_type(drive_path)
                        specific_info = self._get_specific_info(drive_path, self.DISK_INSERTED_ALERT_TYPE)
                        resource_id = self._drive_by_path.get(drive_path, str(drive["Id"]))
                        self._send_msg(self.DISK_INSERTED_ALERT_TYPE, resource_type, resource_id, specific_info)
                        self._existing_drive.update({drive_path: False})
                self._update_drive_faults()
                store.put(self._existing_drive, self.disk_cache_path)

            # Retrieve the main loop which will be called in the run method
            self._loop = gobject.MainLoop()

            # Initialize the gobject threads and get its context
            gobject.threads_init()
            context = self._loop.get_context()

            logger.info("DiskMonitor initialization completed")

            # Leave enabled for now, it's not too verbose and handy in logs when status' change
            self._set_debug(True)
            self._set_debug_persist(True)

            # Loop forever iterating over the context
            while self._running == True:
                context.iteration(False)
                time.sleep(self._thread_sleep)

                # Perform SMART tests and refresh drive list on a regular interval
                if datetime.now() > self._next_smart_tm:
                    self._init_drives(stagger=True)

                # Process any msgs sent to us
                self._check_msg_queue()
                with self._drive_info_lock:
                    self._update_drive_faults()
                    store.put(self._existing_drive, self.disk_cache_path)

                # Safe guard to slow the thread down after busy exp resets
                # self._thread_speed_safeguard += 1
                # Only allow to run full throttle for 3 minutes (enough to handle exp resets)
                # if self._thread_speed_safeguard > 18_00:   # 1800 = 10 * 60 * 3 running at .10 delay full speed
                #     self._thread_speed_safeguard = 0
                #     # Slow the main thread down to save on CPU as it gets sped up on drive removal
                #     self._thread_sleep = 5.0

            self._log_debug("DiskMonitor gracefully breaking out " \
                                "of dbus Loop, not restarting.")

        except Exception as ae:
            # Check for debug mode being activated when it breaks out of blocking loop
            self._read_my_msgQ_noWait()
            if self.is_running() is True:
                self._log_debug(f"Ungracefully breaking out of dbus loop with error: {ae}")
                # Let the top level sspl_ll_d know that we have a fatal error
                #  and shutdown so that systemd can restart it
                raise Exception(ae)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        self._log_debug("Finished processing successfully")

    def _check_msg_queue(self):
        """Handling incoming JSON msgs"""

        # Process until our message queue is empty
        while not self._is_my_msgQ_empty():
            jsonMsg, _ = self._read_my_msgQ()
            if jsonMsg is not None:
                self._process_msg(jsonMsg)

    def _process_msg(self, jsonMsg):
        """Process various messages sent to us on our msg queue"""
        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        if jsonMsg.get("sensor_request_type") is not None:
            sensor_request_type = jsonMsg.get("sensor_request_type")
            self._log_debug(f"_processMsg, sensor_request_type: {sensor_request_type}")

            # Serial number is used as an index into dicts
            jsonMsg_serial_number = jsonMsg.get("serial_number")
            self._log_debug(f"_processMsg, serial_number: {jsonMsg_serial_number}")

            # Parse out the UUID and save to send back in response if it's available
            uuid =  "Not-Found"
            if jsonMsg.get("uuid") is not None:
                uuid = jsonMsg.get("uuid")
            self._log_debug(f"_processMsg, sensor_request_type: {sensor_request_type}, uuid: {uuid}")

            # Refresh the set of managed systemd objects
            self._disk_objects = self._disk_manager.GetManagedObjects()

            # Get a list of all the drive devices available in systemd
            re_drive = re.compile('(?P<path>.*?/drives/(?P<id>.*))')
            drives = [m.groupdict() for m in
                  [re_drive.match(path) for path in list(self._disk_objects.keys())]
                  if m]

            if sensor_request_type == "simulate_failure":
                # Handle simulation requests
                sim_request = jsonMsg.get("node_request")
                self._log_debug(f"_processMsg, Starting simulating failure: {sim_request}")
                if sim_request == "SMART_FAILURE":
                    # Append to list of drives requested to simulate failure
                    self._simulated_smart_failures.append(jsonMsg_serial_number)

            elif sensor_request_type == "resend_drive_status":
                self._log_debug(f"_processMsg, resend_drive_status: {jsonMsg_serial_number}")
                for drive in drives:
                    try:
                        if self._disk_objects[drive['path']].get('org.freedesktop.UDisks2.Drive') is not None:
                            # Get the drive's serial number
                            udisk_drive = self._disk_objects[drive['path']]['org.freedesktop.UDisks2.Drive']
                            serial_number = str(udisk_drive["Serial"])

                            # If serial number is not present then use the ending of by-id symlink
                            if len(serial_number) == 0:
                                tmp_serial = str(self._drive_by_id[drive['path']].split("/")[-1])

                                # Serial numbers are limited to 20 chars string with drive keyword
                                serial_number = tmp_serial[tmp_serial.rfind("drive"):]

                            if jsonMsg_serial_number == serial_number:
                                # Generate and send an internal msg to DiskMsgHandler that the drive is available
                                self._notify_disk_msg_handler(drive['path'], "OK_None", serial_number)

                                # Notify internal msg handlers who need to map device name to serial numbers
                                self._notify_msg_handler_sn_device_mappings(drive['path'], serial_number)
                    except Exception as ae:
                        self._log_debug(f"_process_msg, resend_drive_status, Exception: {ae}")

            elif sensor_request_type == "disk_smart_test":
                # No need to validate for serial if SMART is not supported.
                if not self._smart_supported:
                    # Create the request to be sent back
                    request = f"SMART_TEST: {jsonMsg_serial_number}"
                    # Send an Ack msg back with SMART results as Unsupported
                    json_msg = AckResponseMsg(request, self.SMART_STATUS_UNSUPPORTED, "").getJson()
                    self._write_internal_msgQ(EgressProcessor.name(), json_msg)
                    return

                self._log_debug("_processMsg, Starting SMART test")
                # If the serial number is an asterisk then schedule smart tests on all drives
                if jsonMsg_serial_number == "*":
                    self._smart_jobs = {}

                # Loop through all the drives and initiate a SMART test
                for drive in drives:
                    try:
                        serial_number = None
                        if self._disk_objects[drive['path']].get('org.freedesktop.UDisks2.Drive') is not None:
                            # Get the drive's serial number
                            udisk_drive = self._disk_objects[drive['path']]['org.freedesktop.UDisks2.Drive']
                            serial_number = str(udisk_drive["Serial"])

                            if len(serial_number) == 0:
                                self._log_debug("_init_drives, couldn't get serial number. Extracting from by-id link")
                                by_id_link = str(self._drive_by_id.get(drive['path'], ""))
                                if len(by_id_link) != 0:
                                    tmp_serial = by_id_link.split("/")[-1]

                                    # Serial numbers are limited to 20 chars string with drive keyword
                                    start_index = tmp_serial.rfind("drive")
                                    if start_index != -1:
                                        serial_number = tmp_serial[start_index:].strip()
                                else:
                                    self._log_debug(
                                        f"_init_drives, couldn't extract serial number from by-id link for drive path {drive['path']} ")

                            if len(serial_number) > 0:
                                # Found the drive requested or it's an * indicating all drives
                                if jsonMsg_serial_number == serial_number or \
                                    jsonMsg_serial_number == "*":

                                    # Associate the uuid to the drive path for the ack msg being sent back from request
                                    self._smart_uuids[uuid] = serial_number

                                    # Schedule a SMART test to begin, if requesting all drives then stagger possibly?
                                    self._schedule_SMART_test(drive['path'], serial_number=serial_number)

                    except Exception as ae:
                        self._log_debug(f"_process_msg, Exception: {ae}")
                        try:
                            # If the error is not a duplicate request for running a test then send back an error
                            if "already SMART self-test running" not in str(ae):
                                request  = f"SMART_TEST: {serial_number}"
                                response = "Failed"

                                # Send an Ack msg back with SMART results
                                json_msg = AckResponseMsg(request, response, uuid).getJson()
                                self._write_internal_msgQ(EgressProcessor.name(), json_msg)

                                # Remove from our list if it's present
                                serial_number = self._smart_uuids.get(uuid)
                                if serial_number is not None:
                                    self._smart_uuids[uuid] = None

                        except Exception as e:
                            self._log_debug(f"_process_msg, Exception: {e}")

    def _update_by_id_paths(self):
        """Updates the global dict of by-id symlinks for each drive"""

        # Refresh the set of managed systemd objects
        self._disk_objects = self._disk_manager.GetManagedObjects()

        # Get a list of all the block devices available in systemd
        re_blocks = re.compile('(?P<path>.*?/block_devices/(?P<id>.*))')
        block_devs = [m.groupdict() for m in
                      [re_blocks.match(path) for path in list(self._disk_objects.keys())]
                      if m]

        # Retrieve the by-id symlink for each drive and save in a dict with the drive path as key
        for block_dev in block_devs:
            try:
                if self._disk_objects[block_dev['path']].get('org.freedesktop.UDisks2.Block') is not None:
                    # Obtain the list of symlinks for the block device
                    udisk_block = self._disk_objects[block_dev['path']]["org.freedesktop.UDisks2.Block"]
                    symlinks = self._sanitize_dbus_value(udisk_block["Symlinks"])

                    # Parse out the wwn symlink if it exists otherwise use the by-id
                    for symlink in symlinks:
                        if "wwwn" in symlink:
                            self._drive_by_id[udisk_block["Drive"]] = symlink
                        elif "by-id" in symlink:
                            self._drive_by_id[udisk_block["Drive"]] = symlink
                        # TODO:  Improve logic for getting resource_id
                        # Current approch for getting resource_id is to check "phy" in by-path
                        # symlink. If "phy" is in by-path use path of that drive for resource_id
                        elif "by-path" in symlink:
                            if "phy" in symlink:
                                self._drive_by_path[udisk_block["Drive"]] = symlink[len("/dev/disk/by-path/"):]

                    # Maintain a dict of device names
                    device = self._sanitize_dbus_value(udisk_block["Device"])
                    self._drive_by_device_name[udisk_block["Drive"]] = device

            except Exception as ae:
                self._log_debug("block_dev unusable: %r" % ae)

    def _schedule_SMART_test(self, drive_path, test_type ="short", serial_number =None):
        """Schedules a SMART test to be executed on a drive
           add_interface/remove_interface is the callback
           on completion
        """
        if self._disk_objects[drive_path].get('org.freedesktop.UDisks2.Drive.Ata') is not None:
            self._log_debug(f"Running SMART on drive: {drive_path}")

            # Obtain an interface to the ATA drive and start the SMART test
            dev_obj = self._bus.get_object('org.freedesktop.UDisks2', drive_path)
            idev_obj = Interface(dev_obj, 'org.freedesktop.UDisks2.Drive.Ata')
            idev_obj.SmartSelftestStart(test_type, {})

        # A request was received to run a SMART test on a SAS drive (RAID drives)
        elif serial_number is not None:
            # Retrieve the device name for the disk
            device_name = self._drive_by_device_name[drive_path]
            self._log_debug(f"Running SMART on SAS drive path: {drive_path}, dev name: {device_name}")

            # Schedule a smart test to be run
            command = f"/usr/sbin/smartctl -t short -d scsi {device_name}"
            response, error = self._run_command(command)

            ack_response = "Passed"
            status_reason = "OK_None"
            if len(error) > 0:
                self._log_debug(f"Error running SMART on SAS drive: {error}")
                status_reason = "Failed_smart_unknown"
                ack_response  = "Failed"
            else:
                # Allow test to run
                time.sleep(60)

                # Get the results of test
                command = f"/usr/sbin/smartctl -H -d scsi {device_name}"
                response, error = self._run_command(command)

                if "SMART Health Status: OK" not in response:
                    self._log_debug(f"Error running SMART on SAS drive: {response}")
                    ack_response  = "Failed"
                    status_reason = "Failed_smart_failure"

            # Generate and send an internal msg to DiskMsgHandler
            self._notify_disk_msg_handler(drive_path, status_reason, serial_number)

            # Create the request to be sent back
            request = f"SMART_TEST: {serial_number}"

            # Loop thru all the uuids awaiting a response and find matching serial number
            for smart_uuid in self._smart_uuids:
                uuid_serial_number = self._smart_uuids.get(smart_uuid)

                # See if we have a match and send out response
                if uuid_serial_number is not None and \
                    serial_number == uuid_serial_number:

                    # Send an Ack msg back with SMART results
                    json_msg = AckResponseMsg(request, ack_response, smart_uuid).getJson()
                    self._write_internal_msgQ(EgressProcessor.name(), json_msg)

                    # Remove from our list
                    self._smart_uuids[smart_uuid] = None

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        response, error = process.communicate()
        return response.rstrip('\n'), error.rstrip('\n'), process.returncode

    def _get_drives(self):
        """
        Get physical drives(server+enclosure) atttached to server
        This will only return server drives if setup is non-JBOD
        returns {
                    "/org/freedesktop/UDisks2/drives/drive_3": {
                        "dbus_info": dbus_properties,
                        "node_disk": False
                    },
                    "/org/freedesktop/UDisks2/drives/ST1000NM0055_1V410C_ZBS1VJHX": {
                        "dbus_info": dbus_properties,
                        "node_disk": True
                    }
                }
        """
        drives = self._disk_manager.GetManagedObjects()

        return {obj_path : { self.DRIVE_DBUS_INFO: interfaces_and_property["org.freedesktop.UDisks2.Drive"],
                             'node_disk': self._is_local_drive(obj_path)}
                        for obj_path, interfaces_and_property in drives.items()
                        if "drive" in obj_path and is_physical_drive(interfaces_and_property["org.freedesktop.UDisks2.Drive"])}

    def _get_resource_type(self, object_path):
        if self._drives[object_path]["node_disk"]:
            return self.NODE_DISK_RESOURCE_TYPE
        else:
            return self.ENCLOSURE_DISK_RESOURCE_TYPE

    def _get_specific_info(self, object_path, alert_type):
        drive = self._drives[object_path]
        drive_dbus_info = drive[self.DRIVE_DBUS_INFO]
        response = {}
        if alert_type in [self.DISK_INSERTED_ALERT_TYPE, self.DISK_REMOVED_ALERT_TYPE]:
            response = json.loads(json.dumps(drive_dbus_info),
                        object_hook=lambda obj : {key.lower(): value for key, value in obj.items()})
        if drive["node_disk"]:
            if alert_type in [self.DISK_FAULT_ALERT_TYPE, self.DISK_FAULT_RESOLVED_ALERT_TYPE]:
                response = {"health_status" : drive[self.DRIVE_FAULT_ATTR]}
            return response
        else:
            health = "Fault" if alert_type in [self.DISK_FAULT_ALERT_TYPE, \
                                        self.DISK_REMOVED_ALERT_TYPE] else "OK"
            size = '{0:.2f} TB'.format(int(drive_dbus_info["Size"])/ 1024 ** 4)
            specific_info = {
                    "location" : self._drive_by_path.get(object_path, ""),
                    "serial_number" : str(drive_dbus_info["Serial"]),
                    "size" : size,
                    "slot" : "",
                    "health" : health,
                    "health_reason": "",
                    "health_recommendation": ""}
            return {**response, **specific_info}

    def _init_drives(self, stagger=False):
        """Notifies DiskMsgHanlder of available drives and schedules a short SMART test"""

        # Update the drive's by-id symlink paths
        self._update_by_id_paths()

        # Good for debugging and seeing values available in all the interfaces so keeping here
        #for object_path, interfaces_and_properties in self._disk_objects.items():
        #    self._print_interfaces_and_properties(interfaces_and_properties)

        # Get a list of all the drive devices available in systemd
        re_drive = re.compile('(?P<path>.*?/drives/(?P<id>.*))')
        drives = [m.groupdict() for m in
                  [re_drive.match(path) for path in list(self._disk_objects.keys())]
                  if m]

        # Loop through all the drives and initiate a SMART test
        self._smart_jobs : {}
        for drive in drives:
            try:
                if self._disk_objects[drive['path']].get('org.freedesktop.UDisks2.Drive') is not None:
                    # Get the drive's serial number
                    udisk_drive = self._disk_objects[drive['path']]['org.freedesktop.UDisks2.Drive']
                    serial_number = str(udisk_drive["Serial"])

                    if len(serial_number) == 0:
                        self._log_debug("_init_drives, couldn't get serial number. Extracting from by-id link")
                        by_id_link = str(self._drive_by_id.get(drive['path'], ""))
                        if len(by_id_link) != 0:
                            tmp_serial = by_id_link.split("/")[-1]

                            # Serial numbers are limited to 20 chars string with drive keyword
                            start_index = tmp_serial.rfind("drive")
                            if start_index != -1:
                                serial_number = tmp_serial[start_index:].strip()
                        else:
                            self._log_debug(
                                f"_init_drives, couldn't extract serial number from by-id link for drive path {drive['path']}")

                    if len(serial_number) > 0:
                        # Generate and send an internal msg to DiskMsgHandler that the drive is available
                        self._notify_disk_msg_handler(drive['path'], "OK_None", serial_number)

                        # Notify internal msg handlers who need to map device name to serial numbers
                        self._notify_msg_handler_sn_device_mappings(drive['path'], serial_number)

                    # SMART test is not supported in VM environment
                    if self._smart_supported and self._run_smart_on_start:
                        # Schedule a SMART test to begin, if regular intervals then stagger
                        if stagger:
                            time.sleep(10)
                        self._schedule_SMART_test(drive['path'])

            except Exception as ae:
                self._log_debug(f"_init_drives, Exception: {ae}")

        # Update the next time to run SMART tests
        self._next_smart_tm = datetime.now() + timedelta(seconds=self._smart_interval)

    def _interface_added(self, object_path, interfaces_and_properties):
        """Callback for when an interface like drive or SMART job has been added"""
        try:
            self._log_debug(f"Interface Added, Object Path: {object_path}, interfaces_and_properties {interfaces_and_properties}")
            # Handle drives added
            if interfaces_and_properties.get("org.freedesktop.UDisks2.Drive") is not None and \
                is_physical_drive(interfaces_and_properties.get("org.freedesktop.UDisks2.Drive")):
                self._update_by_id_paths()

                serial_number = str(interfaces_and_properties['org.freedesktop.UDisks2.Drive']['Serial'])

                # If serial number is not present then use the ending of by-id symlink
                if len(serial_number) == 0:
                    tmp_serial = str(self._drive_by_id[object_path].split("/")[-1])

                    # Serial numbers are limited to 20 chars string with drive keyword
                    serial_number = tmp_serial[tmp_serial.rfind("drive"):]
                    interfaces_and_properties['org.freedesktop.UDisks2.Drive']['Serial'] = serial_number

                with self._drive_info_lock:
                    # Update drives
                    self._drives[object_path] = {}
                    self._drives[object_path][self.DRIVE_DBUS_INFO] = interfaces_and_properties['org.freedesktop.UDisks2.Drive']

                    drive = self._drives[object_path][self.DRIVE_DBUS_INFO]
                    if self._is_local_drive(object_path):
                        self._drives[object_path]["node_disk"] = True

                    resource_type = self._get_resource_type(object_path)
                    specific_info = self._get_specific_info(object_path, self.DISK_INSERTED_ALERT_TYPE)
                    resource_id = self._drive_by_path.get(object_path, str(drive["Id"]))
                    self._send_msg(self.DISK_INSERTED_ALERT_TYPE, resource_type, resource_id, specific_info)

                    # Update cache with latest info
                    self._existing_drive.update({object_path: False})
                    self._update_drive_faults()
                    store.put(self._existing_drive, self.disk_cache_path)

            # Handle jobs like SMART tests being initiated
            elif interfaces_and_properties.get("org.freedesktop.UDisks2.Job") is not None:
               Iprops = interfaces_and_properties.get("org.freedesktop.UDisks2.Job")
               if Iprops.get("Operation") is not None and \
                    Iprops.get("Operation") == "ata-smart-selftest":

                # Save Job properties for use when SMART test finishes
                self._smart_jobs[object_path] = Iprops

                # Display info about the SMART test starting
                self._print_interfaces_and_properties(interfaces_and_properties)

        except Exception as ae:
            self._log_debug("_interface_added: Exception: %r" % ae)

    def _interface_removed(self, object_path, interfaces):
        """Callback for when an interface like drive or SMART job has been removed"""
        self._log_debug(f"Interface Removed, Object Path: {object_path}, interfaces: {interfaces}")
        for interface in interfaces:
            try:
                # Handle drives removed
                if interface == "org.freedesktop.UDisks2.Drive":
                    with self._drive_info_lock:
                        # If drive is removed, thread will run with .10 sleep
                        # commenting this to save CPU time
                        # Speed thread up in case we have multiple drive removal events queued up
                        # self._thread_sleep = .10

                        # Commenting below code as we dont have .10 sleep on drive removal
                        # Only allow it to run full speed temporarily in order to handle exp resets
                        # self._thread_speed_safeguard = 0

                        # If object_path is not in self._drives. No need to generate alert
                        # as removed disk is remote disk
                        try:
                            drive = self._drives[object_path][self.DRIVE_DBUS_INFO]
                        except KeyError:
                            self._log_debug(f"Object is not present in drives info {self._drives.keys()}, ignoring signal")
                            continue
                        serial_number = str(drive["Serial"])

                        self._log_debug("Drive Interface Removed")
                        self._log_debug(f"  Object Path: {object_path}")
                        self._log_debug(f"  Serial Number: {serial_number}")

                        resource_type = self._get_resource_type(object_path)

                        # Generate and send an internal msg to DiskMsgHandler
                        specific_info = self._get_specific_info(object_path, self.DISK_REMOVED_ALERT_TYPE)
                        resource_id = self._drive_by_path.get(object_path, str(drive["Id"]))
                        self._send_msg(self.DISK_REMOVED_ALERT_TYPE, resource_type, resource_id, specific_info)

                        # Remove drive
                        del self._drives[object_path]

                        # Update cache with latest info
                        del self._existing_drive[object_path]
                        self._update_drive_faults()
                        store.put(self._existing_drive, self.disk_cache_path)

                # Handle jobs completed like SMART tests
                elif interface == "org.freedesktop.UDisks2.Job":
                    # If we're doing SMART tests then slow the thread down to save on CPU
                    # self._thread_sleep = 1.0

                    # Retrieve the saved SMART data when the test was started
                    smart_job = self._smart_jobs.get(object_path)
                    if smart_job is None:
                        self._log_debug(f"SMART job not found, ignoring: {object_path}")
                        return
                    self._smart_jobs[object_path] = None

                    # Loop through all the currently managed objects and retrieve the smart status
                    for disk_path, interfaces_and_properties in list(self._disk_objects.items()):
                        if disk_path in smart_job["Objects"]:
                            # Get the SMART test results and the serial number
                            udisk_drive     = self._disk_objects[disk_path]['org.freedesktop.UDisks2.Drive']
                            udisk_drive_ata = self._disk_objects[disk_path]['org.freedesktop.UDisks2.Drive.Ata']
                            smart_status    = str(udisk_drive_ata["SmartSelftestStatus"])
                            serial_number   = str(udisk_drive["Serial"])

                            # If serial number is not present then use the ending of by-id symlink
                            if serial_number is None or \
                                len(serial_number) == 0:
                                tmp_serial = disk_path.split("/")[-1]

                                # Serial number is past the last underscore
                                serial_number = tmp_serial.split("_")[-1]

                            # Check for simulated SMART failure for Halon
                            if serial_number in self._simulated_smart_failures:
                                self._simulated_smart_failures.remove(serial_number)
                                self._log_debug("SIMULATING SMART failure for Halon")
                                response     = "Failed"
                                smart_status = "fatal"
                            else:
                                # If ther is no status then test did not fail
                                if len(smart_status) == 0:
                                    response     = "Passed"
                                    smart_status = "success"
                                elif "error" in smart_status.lower() or \
                                    "fatal" in smart_status.lower():
                                    response = "Failed"
                                else:
                                    response = "Passed"

                            self._log_debug("SMART Job Interface Removed")
                            self._log_debug(f"  Object Path: {object_path}")
                            self._log_debug(f"  Serial Number: {serial_number}, SMART status: {smart_status}")

                            # Proccess the SMART result
                            self._process_smart_status(disk_path, smart_status, serial_number)

                            # Create the request to be sent back
                            request = f"SMART_TEST: {serial_number}"

                            # Loop thru all the uuids awaiting a response and find matching serial number
                            for smart_uuid in self._smart_uuids:
                                uuid_serial_number = self._smart_uuids.get(smart_uuid)

                                # See if we have a match and send out response
                                if uuid_serial_number is not None and \
                                    serial_number == uuid_serial_number:

                                    # Send an Ack msg back with SMART results
                                    json_msg = AckResponseMsg(request, response, smart_uuid).getJson()
                                    self._write_internal_msgQ(EgressProcessor.name(), json_msg)

                                    # Remove from our list
                                    self._smart_uuids[smart_uuid] = None

                else:
                    self._log_debug("Systemd Interface Removed")
                    self._log_debug(f"  Object Path: {object_path}")

            except Exception as ae:
                self._log_debug(f"interface_removed: Exception: {ae}") # Drive was removed during SMART?
                self._log_debug("Possible cause: Job not found because service was recently restarted")

    def _process_smart_status(self, disk_path, smart_status, serial_number):
        """Create the status_reason field and notify disk msg handler"""

        # Possible SMART status for systemd described at
        # http://udisks.freedesktop.org/docs/latest/gdbus-org.freedesktop.UDisks2.
        # Drive.Ata.html#gdbus-property-org-freedesktop-UDisks2-Drive-Ata.SmartSelftestStatus
        if smart_status.lower() == "success" or \
            smart_status.lower() == "inprogress":
            status_reason = "OK_None"
        elif smart_status.lower() == "interrupted":
            # Ignore if the test was interrupted, not conclusive
            return
        elif smart_status.lower() == "aborted":
            self._log_debug(f"SMART test aborted on drive, rescheduling: {serial_number}")
            self._schedule_SMART_test(disk_path)
            return
        elif smart_status.lower() == "fatal":
            status_reason = "Failed_smart_failure"
        elif smart_status.lower() == "error_unknown":
            status_reason = "Failed_smart_unknown"
        elif smart_status.lower() == "error_electrical":
            status_reason = "Failed_smart_electrical_failure"
        elif smart_status.lower() == "error_servo":
            status_reason = "Failed_smart_servo_failure"
        elif smart_status.lower() == "error_read":
            status_reason = "Failed_smart_error_read"
        elif smart_status.lower() == "error_handling":
            status_reason = "Failed_smart_damage"
        else:
            status_reason = f"Unknown smart status: {smart_status}_unknown"

        # Generate and send an internal msg to DiskMsgHandler
        self._notify_disk_msg_handler(disk_path, status_reason, serial_number)

    def _notify_disk_msg_handler(self, disk_path, status_reason, serial_number):
        """Sends an internal msg to DiskMsgHandler with a drives status"""

        # Retrieve the by-id simlink for the disk
        path_id = self._drive_by_id[disk_path]

        internal_json_msg = {"sensor_response_type" : "disk_status_drivemanager",
                             "status" : status_reason,
                             "serial_number" : serial_number,
                             "path_id" : path_id
                             }

        # Send the event to disk message handler to generate json message
        self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

    def _send_msg(self, alert_type, resource_type, resource_id, specific_info):
        """Sends an internal msg to DiskMsgHandler"""

        if alert_type == self.DISK_FAULT_ALERT_TYPE:
            description = "Fault detected for server drive."
        elif alert_type == self.DISK_FAULT_RESOLVED_ALERT_TYPE:
            description = "Fault resolved for server drive."
        elif alert_type == self.DISK_INSERTED_ALERT_TYPE:
            description = "Server drive is inserted."
        elif alert_type == self.DISK_REMOVED_ALERT_TYPE:
            description = "Server drive is missing."
        else:
            description = "Server drive alert."

        event_time = str(int(time.time()))
        severity_reader = SeverityReader()
        msg =  {"sensor_response_type" : "node_disk",
               "response" : {
                    "alert_type": alert_type,
                    "severity": severity_reader.map_severity(alert_type),
                    "alert_id": MonUtils.get_alert_id(event_time),
                    "host_id": self.os_utils.get_fqdn(),
                    "info": {
                        "resource_type": resource_type,
                        "resource_id": resource_id,
                        "event_time": event_time,
                        "description": description
                        },
                    "specific_info": specific_info
                    }
                }
        # Send the event to disk message handler to generate json message
        self._write_internal_msgQ(DiskMsgHandler.name(), msg)

    def _notify_msg_handler_sn_device_mappings(self, disk_path, serial_number):
        """Sends an internal msg to handlers who need to maintain a
            mapping of serial numbers to device names
        """

        # Retrieve the device name for the disk
        device_name = self._drive_by_device_name[disk_path]

        # Retrieve the by-id simlink for the disk
        drive_byid = self._drive_by_id[disk_path]

        internal_json_msg = {"sensor_response_type" : "devicename_serialnumber",
                             "serial_number" : serial_number,
                             "device_name" : device_name,
                             "drive_byid" : drive_byid
                             }

        # Send the event to Node Data message handler to generate json message
        self._write_internal_msgQ(NodeDataMsgHandler.name(), internal_json_msg)

    def _sanitize_dbus_value(self, value):
        """Convert certain DBus type combinations so that they are easier to read"""
        if isinstance(value, Array) and value.signature == "ay":
            try:
                return self._decode_ay(value)
            except:
                # Try an array of arrays; 'aay' which is the symlinks
                return list(map(self._decode_ay, value or ()))
        elif isinstance(value, Array) and value.signature == "y":
            return bytearray(value).rstrip(bytearray((0,))).decode('utf-8')
        else:
            return value

    def _decode_ay(self, value):
        """Convert binary blob from DBus queries to strings"""
        if len(value) == 0 or \
           value is None:
            return ''
        elif isinstance(value, str):
            return value
        elif isinstance(value, bytes):
            return value.decode('utf-8')
        else:
            # dbus.Array([dbus.Byte]) or any similar sequence type:
            return bytearray(value).rstrip(bytearray((0,))).decode('utf-8')

    def _print_interfaces_and_properties(self, interfaces_and_properties):
        """
        Print a collection of interfaces and properties exported by some object

        The argument is the value of the dictionary _values_, as returned from
        GetManagedObjects() for example. See this for details:
            http://dbus.freedesktop.org/doc/dbus-specification.html#standard-interfaces-objectmanager
        """
        for interface_name, properties in list(interfaces_and_properties.items()):
            self._log_debug(f"  Interface {interface_name}")
            for prop_name, prop_value in list(properties.items()):
                prop_value = self._sanitize_dbus_value(prop_value)
                self._log_debug(f"  {prop_name}: {prop_value}")

    def _getSMART_interval(self):
        """Retrieves the frequency to run SMART tests on all the drives"""
        smart_interval = int(Conf.get(SSPL_CONF, f"{self.DISKMONITOR}>{self.SMART_TEST_INTERVAL}",
                                                         86400))
        # Add a sanity check to avoid constant looping, 15 minute minimum (900 secs)
        if smart_interval < 900:
            smart_interval = 86400
        return smart_interval

    def _can_run_smart_on_start(self):
        """Retrieves value of "run_smart_on_start" from configuration file.Returns
           True|False based on that.
        """
        run_smart_on_start = Conf.get(SSPL_CONF, f"{self.DISKMONITOR}>{self.SMART_ON_START}",
                                                         "False")
        run_smart_on_start = run_smart_on_start.lower()
        if run_smart_on_start == 'true':
            return True
        if run_smart_on_start != 'false':
            logger.warn(
                f"Invalid configuration ({run_smart_on_start}) for run_smart_on_start. Assuming False")
        return False

    # TODO handle boolean values from conf file
    def _getShort_SMART_enabled(self):
        """Retrieves the flag indicating to run short tests periodically"""
        smart_interval = int(Conf.get(SSPL_CONF, f"{self.DISKMONITOR}>{self.SMART_SHORT_ENABLED}",
                                                         86400))
        return smart_interval

    def _getConveyance_SMART_enabled(self):
        """Retrieves the flag indicating to run conveyance tests when a disk is inserted"""
        smart_interval = int(Conf.get(SSPL_CONF, f"{self.DISKMONITOR}>{self.SMART_CONVEYANCE_ENABLED}",
                                                         86400))
        # Add a sanity check to avoid constant looping, 15 minute minimum (900 secs)
        if smart_interval < 900:
            smart_interval = 900
        return smart_interval

    def _is_smart_supported(self):
        """Retrieves the current setup. This was added to not to run actual SMART test
           in VM environment because virtual drives don't support SMART test.
        """
        smart_supported = True
        # check on environment
        result, _, _ = self._run_command("sudo facter is_virtual")
        if result:
            if 'true' in result[0]:
                smart_supported = False
        return smart_supported

    def _update_drive_faults(self):
        # This function makes 2 assumptions:
        # 1. self._drive_info_lock is held by the caller
        # 2. self._drives and self._existing_drive are consistent with each other.

        if not self._smart_supported:
            return

        for object_path in self._drives.keys():

            # To handle case when drive is removed, but interface_removed function is not yet
            # called, so drive will be still in self._drives, but smartctl command will fail as
            # device is removed.
            if not self._drives[object_path]["node_disk"]:
                cmd = f"sudo smartctl -d scsi -H {self._drive_by_device_name[object_path]} --json"
            else:
                cmd = f"sudo smartctl -H {self._drive_by_device_name[object_path]} --json"
            response, err, retcode = self._run_command(cmd)
            if retcode != 0 and err:
                self._iem.iem_fault("SMARTCTL_ERROR")
                if self.SMARTCTL not in self._iem.fault_iems:
                    self._iem.fault_iems.append(self.SMARTCTL)
                return
            if retcode == 0 and response and self.SMARTCTL in self._iem.fault_iems:
                self._iem.iem_fault_resolved("SMARTCTL_AVAILABLE")
                self._iem.fault_iems.remove(self.SMARTCTL)

            response = json.loads(response)
            try:
                if "No such device" in response["smartctl"]["message"][0]["string"]:
                    logger.debug(f"DiskMonitor, _update_drive_faults, drive {object_path} is removed, ignoring SMART test")
                    continue
            # If smratctl command is not failing there will be no ["smartctl"]["message"][0]["string"] in response
            except (KeyError, IndexError):
                try:
                    is_drive_faulty = not response['smart_status']['passed']
                # If ['smart_status']['passed'] not present in response, consider it as fault
                except KeyError:
                    is_drive_faulty = True

            if not self._existing_drive[object_path] and is_drive_faulty:
                self._existing_drive[object_path] = True
                self._drives[object_path][self.DRIVE_FAULT_ATTR] = self._get_drive_fault_info(object_path)
                resource_type = self._get_resource_type(object_path)
                specific_info = self._get_specific_info(object_path, self.DISK_FAULT_ALERT_TYPE)
                resource_id = self._drive_by_path.get(object_path,
                                    str(self._drives[object_path][self.DRIVE_DBUS_INFO]["Id"]))
                self._send_msg(self.DISK_FAULT_ALERT_TYPE,
                               resource_type,
                               resource_id,
                               specific_info)
            elif self._existing_drive[object_path] and not is_drive_faulty:
                self._existing_drive[object_path] = False
                self._drives[object_path][self.DRIVE_FAULT_ATTR] = self._get_drive_fault_info(object_path)
                resource_type = self._get_resource_type(object_path)
                specific_info = self._get_specific_info(object_path, self.DISK_FAULT_RESOLVED_ALERT_TYPE)
                resource_id = self._drive_by_path.get(object_path,
                                    str(self._drives[object_path][self.DRIVE_DBUS_INFO]["Id"]))
                self._send_msg(self.DISK_FAULT_RESOLVED_ALERT_TYPE,
                                resource_type,
                               resource_id,
                               specific_info)
            # else no change

    def _is_drive_faulty(self, path):
        if not self._drives[path]["node_disk"]:
            cmd = f"sudo smartctl -d scsi -H {self._drive_by_device_name[path]} --json"
        else:
            cmd = f"sudo smartctl -H {self._drive_by_device_name[path]} --json"
        response, _, _ = self._run_command(cmd)
        response = json.loads(response)
        smart_status = response['smart_status']['passed']
        return not smart_status

    def _get_drive_fault_info(self, path):
        if not self._drives[path]["node_disk"]:
            cmd = f"sudo smartctl -d scsi -A {self._drive_by_device_name[path]}"
        else:
            cmd = f"sudo smartctl -A {self._drive_by_device_name[path]}"
        response, err, retcode = self._run_command(cmd)
        if retcode != 0 and err:
            self._iem.iem_fault("SMARTCTL_ERROR")
            if self.SMARTCTL not in self._iem.fault_iems:
                self._iem.fault_iems.append(self.SMARTCTL)
        if retcode == 0 and self.SMARTCTL in self._iem.fault_iems:
            self._iem.iem_fault_resolved("SMARTCTL_AVAILABLE")
            self._iem.fault_iems.remove(self.SMARTCTL)
        return response

    def _is_local_drive(self, object_path):
        """
        Detect Node server local drives using Hdparm tool.
        Hdparm tool give information only for node drive.
        For external JBOD/virtual drives it will give output as:
        "SG_IO: bad/missing sense data "
        Hdparm does not have support for NVME drives, for this drives it gives o/p as:
        "failed: Inappropriate ioctl for device"
        """
        DISK_ERR_MISSING_SENSE_DATA = "SG_IO: bad/missing sense data"
        DISK_ERR_GET_ID_FAILURE = "HDIO_GET_IDENTITY failed: Invalid argument"
        drive_name = self._drive_by_device_name[object_path]
        cmd = f'sudo hdparm -i {drive_name}'
        res, err, retcode = self._run_command(cmd)
        if retcode == 0:
            if self.HDPARM in self._iem.fault_iems:
                self._iem.iem_fault_resolved("HDPARM_AVAILABLE")
                self._iem.fault_iems.remove(self.HDPARM)
            return True
        else:
            logger.debug(f"DiskMonitor, _is_local_drive: Error for drive \
                {drive_name}, ERROR: {err}")
            # TODO : In case of different error(other than \
            # "SG_IO: bad/missing sense data") for local drives,
            # this check would fail.
            if DISK_ERR_MISSING_SENSE_DATA not in err and \
                DISK_ERR_GET_ID_FAILURE not in err:
                # Raise IEM if hdparm gives error other than
                # "SG_IO: bad/missing sense data" or "HDIO_GET_IDENTITY failed:
                #  Invalid argument"
                logger.error("DiskMonitor, _is_local_drive: Error for drive:%s,"
                    "Error: %s, , RESPONSE: %s" %(drive_name, err, res))
                self._iem.iem_fault("HDPARM_ERROR")
                if self.HDPARM not in self._iem.fault_iems:
                    self._iem.fault_iems.append(self.HDPARM)
                return True
            else:
                return False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DiskMonitor, self).shutdown()

def is_physical_drive(interfaces_and_property):
    """
    Get the physical drives attached to server
    WWN is 32 hex characters for the disk which is attached through RAID
    controller and starts with 0x6. In JBOD setup drives will be directly
    attached to server so it's WWN will be 16 hex charactes and will starts with 0x5
    In JBOD setup this will return server+storage_enclosure drive and in normal
    setup this will return only server drives.

    Drives from JBOD setup (all drives start with 0x5)
    [0:0:1:0]    disk    0x5000c500adff06d3                  /dev/sdb
    [0:0:2:0]    disk    0x5000c500ae9e483f                  /dev/sdc
    [0:0:3:0]    disk    0x5000c500adfed4df                  /dev/sdd

    Drives from non-JBOD setup (drives coming from enclosure starts with 0x6,
                              server drives start with 0x5)
    [0:0:0:0]    disk    0x5000c500c2ecc4b8                  /dev/sda
    [1:0:0:0]    disk    0x5000c500c2ec508b                  /dev/sdbn
    [6:0:1:1]    disk    0x600c0ff00050f0bb13c7505f02000000  /dev/sdr
    """
    return interfaces_and_property["WWN"].startswith("0x5")
