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
  Description:       Monitors Centos 7 systemd for service events and notifies
                    the ServiceMsgHandler.  Detects drive add/remove event,
                    performs SMART on drives and notifies DiskMsgHandler.

 ****************************************************************************
"""
import re
import os
import json
import time
import copy
import subprocess
import threading
import uuid

from datetime import datetime, timedelta

from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from framework.base.module_thread import SensorThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import cs_products, COMMON_CONFIGS
from framework.utils.severity_reader import SeverityReader
from framework.utils.store_factory import store

# Modules that receive messages from this module
from message_handlers.service_msg_handler import ServiceMsgHandler
from message_handlers.disk_msg_handler import DiskMsgHandler
from message_handlers.node_data_msg_handler import NodeDataMsgHandler

from json_msgs.messages.actuators.ack_response import AckResponseMsg

from zope.interface import implementer
from sensors.IService_watchdog import IServiceWatchdog

import dbus
from dbus import SystemBus, Interface, Array
from gi.repository import GObject as gobject
from dbus.mainloop.glib import DBusGMainLoop
import socket

@implementer(IServiceWatchdog)
class SystemdWatchdog(SensorThread, InternalMsgQ):


    SENSOR_NAME       = "SystemdWatchdog"
    PRIORITY          = 2

    # Section and keys in configuration file
    SYSTEMDWATCHDOG    = SENSOR_NAME.upper()
    MONITORED_SERVICES = 'monitored_services'
    SMART_TEST_INTERVAL= 'smart_test_interval'
    SMART_ON_START     = 'run_smart_on_start'
    SYSTEM_INFORMATION = 'SYSTEM_INFORMATION'
    SETUP              = 'setup'

    DEFAULT_RAS_VOL = "/var/cortx/sspl/data/"

    SITE_ID = "site_id"
    RACK_ID = "rack_id"
    NODE_ID = "node_id"
    CLUSTER_ID = "cluster_id"

    DISK_INSERTED_ALERT_TYPE = "insertion"
    DISK_REMOVED_ALERT_TYPE = "missing"

    # SMART test response
    SMART_STATUS_UNSUPPORTED = "Unsupported"

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["ServiceMsgHandler", "DiskMsgHandler", "NodeDataMsgHandler"],
                    "init": ["HPIMonitor"],
                    "rpms": ["smartmontools"]
    }

    DISK_FAULT_ALERT_TYPE = "fault"
    DISK_FAULT_RESOLVED_ALERT_TYPE = "fault_resolved"
    DRIVE_DBUS_INFO = 'dbus_info'
    DRIVE_FAULT_ATTR = 'smart_attributes'
    NODE_DISK_RESOURCE_TYPE = "node:os:disk"

    SMARTCTL_PASSED_RESPONSE = "SMART overall-health self-assessment test result: PASSED"

    @staticmethod
    def name():
        """@return: name of the module."""
        return SystemdWatchdog.SENSOR_NAME

    def __init__(self):
        super(SystemdWatchdog, self).__init__(self.SENSOR_NAME,
                                                  self.PRIORITY)
        # Mapping of services and their status'
        self._service_status = {}

        self._monitored_services = []
        self._inactive_services  = []
        self._wildcard_services  = []

        # Mapping of current service PIDs
        self._service_pids = {}

        # Mapping of SMART jobs and their properties
        self._smart_jobs = {}

        # Mapping of SMART uuids from incoming requests so they can be used in the responses back to halon
        self._smart_uuids = {}

        # List of serial numbers which have been flagged for simulated failure of SMART tests from CLI
        self._simulated_smart_failures = []

        # Delay so thread doesn't spin unnecessarily when not in use.  Startup running quickly to process everything
        self._thread_sleep = 20.0

        # Location of hpi data directory populated by dcs-collector
        self._hpi_base_dir = "/tmp/dcs/hpi"
        self._start_delay = 10



    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(SystemdWatchdog, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(SystemdWatchdog, self).initialize_msgQ(msgQlist)

        # Retrieves the frequency to run SMART tests on all the drives
        self._smart_interval = self._getSMART_interval()

        self._run_smart_on_start = self._can_run_smart_on_start()
        self._log_debug(f"SystemdWatchdog, Run SMART test on start: {self._run_smart_on_start}")

        self._smart_supported = self._is_smart_supported()
        self._log_debug(f"SystemdWatchdog, SMART supported: {self._smart_supported}")

        # Dict of drives by-id symlink from systemd
        self._drive_by_id = {}

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

        self._site_id = conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.SITE_ID,
                                                '0')
        self._rack_id = conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.RACK_ID,
                                                '0')
        self._node_id = conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.NODE_ID,
                                                '0')

        self._cluster_id = conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                self.CLUSTER_ID,
                                                '0')

        self.vol_ras = conf_reader._get_value_with_default(\
            self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get("data_path"), self.DEFAULT_RAS_VOL)

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
                logger.info(f"SystemdWatchdog, dir not found: {self._hpi_base_dir}")
                logger.info(f"SystemdWatchdog, rechecking in {self._start_delay} secs")
                time.sleep(int(self._start_delay))

        # Allow time for the hpi_monitor to come up
        #time.sleep(60)

        return True

    def read_data(self):
        """Return the dict of service status'"""
        return self._service_status

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

            # Get an instance of systemd1
            systemd = self._bus.get_object("org.freedesktop.systemd1", "/org/freedesktop/systemd1")

            # Use the systemd object to get an interface to the Manager
            self._manager = Interface(systemd, dbus_interface='org.freedesktop.systemd1.Manager')

            # Obtain a disk manager interface for monitoring drives
            disk_systemd = self._bus.get_object('org.freedesktop.UDisks2', '/org/freedesktop/UDisks2')
            self._disk_manager = Interface(disk_systemd, dbus_interface='org.freedesktop.DBus.ObjectManager')

            # Assign callbacks to all devices to capture signals
            self._disk_manager.connect_to_signal('InterfacesAdded', self._interface_added)
            self._disk_manager.connect_to_signal('InterfacesRemoved', self._interface_removed)

            # Notify DiskMsgHandler of available drives and schedule SMART tests
            self._init_drives()

            with self._drive_info_lock:
                # Prepare drives to monitor
                self._drives = self._get_local_drives()
                # send msg for new drives
                for drive_path in self._drives.keys():
                    if drive_path not in self._existing_drive:
                        drive = self._drives[drive_path][self.DRIVE_DBUS_INFO]
                        self._send_msg(self.DISK_INSERTED_ALERT_TYPE, str(drive["Id"]), json.loads(json.dumps(drive)))
                        self._existing_drive.update({drive_path: False})
                self._update_drive_faults()
                store.put(self._existing_drive, self.disk_cache_path)

            # Read in the list of services to monitor
            self._monitored_services = self._get_monitored_services()

            # Retrieve a list of all the service units
            units = self._manager.ListUnits()

            # Update the list of monitored services with wildcard entries
            self._add_wildcard_services()

            #  Start out assuming their all inactive
            self._inactive_services = list(self._monitored_services)

            logger.info("Monitoring the following services listed in /etc/sspl.conf:")
            for unit in units:

                if ".service" in unit[0]:
                    unit_name = unit[0]

                    # Apply the filter from config file if present
                    if self._monitored_services:
                        if unit_name not in self._monitored_services:
                            continue
                    logger.debug(f"    {unit_name}")

                    # Retrieve an object representation of the systemd unit
                    unit = self._bus.get_object('org.freedesktop.systemd1',
                                                self._manager.GetUnit(unit_name))

                    state = unit.Get('org.freedesktop.systemd1.Unit', 'ActiveState',
                             dbus_interface='org.freedesktop.DBus.Properties')

                    substate = unit.Get('org.freedesktop.systemd1.Unit', 'SubState',
                             dbus_interface='org.freedesktop.DBus.Properties')

                    self._service_status[str(unit_name)] = str(state) + ":" + str(substate)

                    # Remove it from our inactive list; it's alive and well
                    if state == "active":
                        if unit_name in self._inactive_services:
                            self._inactive_services.remove(unit_name)

                    # Use the systemd unit to get an Interface to call methods
                    Iunit = Interface(unit,
                                      dbus_interface='org.freedesktop.systemd1.Manager')

                    # Connect the PropertiesChanged signal to the unit and assign a callback
                    Iunit.connect_to_signal('PropertiesChanged',
                                            lambda a, b, c, p = unit :
                                            self._on_prop_changed(a, b, c, p),
                                            dbus_interface=dbus.PROPERTIES_IFACE)

                    # Get the current PID of the service
                    curr_pid = self._get_service_pid(unit)

                    # Update the mapping of current pids
                    self._service_pids[str(unit_name)] = curr_pid

                    # Setting service_request to 'status' will case msg handler to retrieve current values
                    msgString = json.dumps({"actuator_request_type": {
                                    "service_watchdog_controller": {
                                        "service_name" : unit_name,
                                        "service_request" : "None",
                                        "state" : state,
                                        "previous_state" : "N/A",
                                        "substate" : substate,
                                        "previous_substate" : "N/A",
                                        "pid" : curr_pid,
                                        "previous_pid" : "N/A"
                                        }
                                    }
                                 })
                    self._write_internal_msgQ(ServiceMsgHandler.name(), msgString)

            # Retrieve the main loop which will be called in the run method
            self._loop = gobject.MainLoop()

            # Initialize the gobject threads and get its context
            gobject.threads_init()
            context = self._loop.get_context()

            logger.info("SystemdWatchdog initialization completed")

            # Leave enabled for now, it's not too verbose and handy in logs when status' change
            self._set_debug(True)
            self._set_debug_persist(True)

            # Loop forever iterating over the context
            step = 0
            while self._running == True:
                context.iteration(False)
                time.sleep(self._thread_sleep)

                if len(self._inactive_services) > 0:
                    self._examine_inactive_services()

                # Perform SMART tests and refresh drive list on a regular interval
                if datetime.now() > self._next_smart_tm:
                    self._init_drives(stagger=True)

                # Search for new wildcard services suddenly appearing, ie m0d@<fid>
                step += 1
                if len(self._wildcard_services) > 0 and step >= 15:
                    step : int = 0
                    self._search_new_services()

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

            self._log_debug("SystemdWatchdog gracefully breaking out " \
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
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)
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
                                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                                # Remove from our list if it's present
                                serial_number = self._smart_uuids.get(uuid)
                                if serial_number is not None:
                                    self._smart_uuids[uuid] = None

                        except Exception as e:
                            self._log_debug(f"_process_msg, Exception: {e}")

    def _add_wildcard_services(self):
        """Update the list of monitored services with wildcard entries"""
        units = self._manager.ListUnits()
        try:
            # Look for wildcards in monitored services list and expandit
            examined_services = copy.deepcopy(self._monitored_services)
            for service in examined_services:
                if "*" in service:
                    # Remove service name from monitored_services and add to wildcard services list
                    self._monitored_services.remove(service)
                    self._wildcard_services.append(service)
                    logger.info(f"Processing wildcard service: {service}")

                    # Search thru list of services on the system that match the starting chars
                    start_chars = service.split("*")[0]
                    logger.info(f"Searching for services starting with: {start_chars}")
                    for unit in units:
                        unit_name = str(unit[0]).split("/")[-1]
                        if unit_name.startswith(start_chars):
                            logger.info(f"    {unit_name}")
                            self._monitored_services.append(unit_name)
        except Exception as ae:
            logger.exception(ae)

    def _search_new_services(self):
        """Look for any new wildcard services, ie m0d@<fid>"""
        units = self._manager.ListUnits()
        #logger.info("Searching for new services")
        #logger.info("inactive_services: %s" % str(self._inactive_services))
        #logger.info("monitored_services: %s" % str(self._monitored_services))
        #logger.info("wildcard_services: %s" % str(self._wildcard_services))

        try:
            for service in self._wildcard_services:
                # Search thru list of services on the system that match the starting chars
                start_chars = service.split("*")[0]
                for unit in units:
                    unit_name = str(unit[0]).split("/")[-1]

                    if unit_name.startswith(start_chars) and \
                       unit_name not in self._monitored_services and \
                       unit_name not in self._inactive_services:
                        logger.info(f"Adding newly found wildcard service: {unit_name}")
                        self._inactive_services.append(unit_name)

        except Exception as ae:
            logger.exception(ae)

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
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                    # Remove from our list
                    self._smart_uuids[smart_uuid] = None

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
        response, error = process.communicate()

        return response.rstrip('\n'), error.rstrip('\n')

    def _get_local_drives(self):

        drives = self._disk_manager.GetManagedObjects()

        local_drives = {obj_path : { self.DRIVE_DBUS_INFO: interfaces_and_property["org.freedesktop.UDisks2.Drive"] }
                        for obj_path, interfaces_and_property in drives.items()
                        if "drive" in obj_path and self._is_local_drive(interfaces_and_property)}
        return local_drives

    # TODO : Improvise local disk detaction.
    # Remove fw version dependency for detecting local disk
    def _is_local_drive(self, interfaces_and_property):
        return "org.freedesktop.UDisks2.Drive.Ata" in interfaces_and_property and \
            str(interfaces_and_property["org.freedesktop.UDisks2.Drive"]["Revision"]) != "G265"

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

    def _examine_inactive_services(self):
        """See if an inactive service has been successfully started
            and if so attach a callback method to its properties
            to detect changes
        """
        examined_services = copy.deepcopy(self._inactive_services)
        for disabled_service in examined_services:
            # Retrieve an object representation of the systemd unit
            unit = self._bus.get_object('org.freedesktop.systemd1',
                                        self._manager.LoadUnit(disabled_service))

            state = unit.Get('org.freedesktop.systemd1.Unit', 'ActiveState',
                             dbus_interface='org.freedesktop.DBus.Properties')

            substate = unit.Get('org.freedesktop.systemd1.Unit', 'SubState',
                             dbus_interface='org.freedesktop.DBus.Properties')

            if state == "active":
                self._log_debug(f"Service: {disabled_service} is now active and being monitored!")
                self._service_status[str(disabled_service)] = str(state) + ":" + str(substate)

                # Use the systemd unit to get an Interface to call methods
                Iunit = Interface(unit,
                                  dbus_interface='org.freedesktop.systemd1.Manager')

                # Connect the PropertiesChanged signal to the unit and assign a callback
                Iunit.connect_to_signal('PropertiesChanged',
                                         lambda a, b, c, p = unit :
                                         self._on_prop_changed(a, b, c, p),
                                         dbus_interface=dbus.PROPERTIES_IFACE)

                # Remove the service from the inactive list and add it to our currently monitored list
                self._inactive_services.remove(disabled_service)
                if disabled_service not in self._monitored_services:
                    self._monitored_services.append(disabled_service)

                # Get the current PID of the service
                curr_pid = self._get_service_pid(unit)

                # Retrieve the previous pid of the service
                prev_pid = self._service_pids.get(str(disabled_service), "N/A")

                # Update the mapping of current pids
                self._service_pids[str(disabled_service)] = curr_pid

                # Send out notification of the state change
                msgString = json.dumps({"actuator_request_type": {
                                    "service_watchdog_controller": {
                                        "service_name" : disabled_service,
                                        "service_request" : "None",
                                        "state" : state,
                                        "previous_state" : "inactive",
                                        "substate" : substate,
                                        "previous_substate" : "dead",
                                        "pid" : curr_pid,
                                        "previous_pid" : prev_pid
                                        }
                                    }
                                 })
                self._write_internal_msgQ(ServiceMsgHandler.name(), msgString)

        if len(self._inactive_services) == 0:
            self._log_debug("Successfully monitoring all services now!")

    def _get_service_pid(self, unit):
        """Returns the current PID of the service"""
        # Get the interface for the unit
        Iunit = Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')

        curr_pid = Iunit.Get('org.freedesktop.systemd1.Service', 'ExecMainPID')
        return str(curr_pid)

    def _get_prop_changed(self, unit, interface, prop_name, changed_properties, invalidated_properties):
        """Retrieves the property that changed"""
        if prop_name in invalidated_properties:
            return unit.Get(interface, prop_name, dbus_interface=dbus.PROPERTIES_IFACE)
        elif prop_name in changed_properties:
            return changed_properties[prop_name]
        else:
            return None

    def _on_prop_changed(self, interface, changed_properties, invalidated_properties, unit):
        """Callback to handle state changes in services"""
        # We currently only care about the unit interface
        if interface != 'org.freedesktop.systemd1.Unit':
            return

        # Get the interface for the unit
        Iunit = Interface(unit, dbus_interface='org.freedesktop.DBus.Properties')

        # Always call methods on the interface not the actual object
        unit_name = str(Iunit.Get(interface, "Id"))

        # Get the state and substate for the service
        state = self._get_prop_changed(unit, interface, "ActiveState",
                                       changed_properties, invalidated_properties)

        substate = self._get_prop_changed(unit, interface, "SubState",
                                          changed_properties, invalidated_properties)

        # Compare prev to curr pids to see if the service restarted abruptly
        curr_pid = self._get_service_pid(unit)

        # Retrieve the previous pid of the service
        prev_pid = self._service_pids.get(unit_name, "N/A")

        # Update the mapping of current pids
        self._service_pids[unit_name] = curr_pid

        # The state can change from an incoming json msg to the service msg handler
        #  This provides a catch to make sure that we don't send redundant msgs
        if self._service_status.get(unit_name, "") == str(state) + ":" + str(substate):
            #self._log_debug("_on_prop_changed, No service state change detected: %s" % unit_name)
            #self._log_debug("\tstate: %s, substate: %s" % (state, substate))
            return

        self._log_debug(f"_on_prop_changed, Service state change detected on unit: {unit_name}")

        # get the previous state and substate for the service
        previous_state = self._service_status.get(unit_name, "N/A:N/A").split(":")[0]
        previous_substate = self._service_status.get(unit_name, "N/A:N/A").split(":")[1]

        self._log_debug(f"_on_prop_changed, State: {state}, Substate: {substate}")
        self._log_debug(f"_on_prop_changed, Previous State: {previous_state}, Previous Substate: {previous_substate}")

        # Update the state in the global dict for later use
        self._service_status[unit_name] = str(state) + ":" + str(substate)

        # Notify the service message handler to transmit the status of the service
        msgString = json.dumps(
                    {"actuator_request_type": {
                        "service_watchdog_controller": {
                            "service_name" : unit_name,
                            "service_request" : "None",
                            "state" : state,
                            "previous_state" : previous_state,
                            "substate" : substate,
                            "previous_substate" : previous_substate,
                            "pid" : curr_pid,
                            "previous_pid" : prev_pid
                            }
                        }
                     })
        self._write_internal_msgQ(ServiceMsgHandler.name(), msgString)

    def _get_monitored_services(self):
        """Retrieves the list of services to be monitored"""
        return self._conf_reader._get_value_list(self.SYSTEMDWATCHDOG,
                                                 self.MONITORED_SERVICES)

    def _interface_added(self, object_path, interfaces_and_properties):
        """Callback for when an interface like drive or SMART job has been added"""
        try:
            self._log_debug("Interface Added")
            self._log_debug("  Object Path: %r" % object_path)

            # Handle drives added
            if interfaces_and_properties.get("org.freedesktop.UDisks2.Drive") is not None and \
                self._is_local_drive(interfaces_and_properties):
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
                    self._drives[object_path][self.DRIVE_DBUS_INFO] = interfaces_and_properties['org.freedesktop.UDisks2.Drive']

                    drive = self._drives[object_path][self.DRIVE_DBUS_INFO]
                    self._send_msg(self.DISK_INSERTED_ALERT_TYPE, str(drive["Id"]), json.loads(json.dumps(drive)))

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
        for interface in interfaces:
            try:
                # Handle drives removed
                if interface == "org.freedesktop.UDisks2.Drive":
                    with self._drive_info_lock:
                        # Speed thread up in case we have multiple drive removal events queued up
                        self._thread_sleep = .10

                        # Only allow it to run full speed temporarily in order to handle exp resets
                        self._thread_speed_safeguard = 0

                        # If object_path is not in self._drives. No need to generate alert
                        # as removed disk is remote disk
                        try:
                            drive = self._drives[object_path][self.DRIVE_DBUS_INFO]
                        except KeyError:
                            continue
                        serial_number = str(drive["Serial"])

                        self._log_debug("Drive Interface Removed")
                        self._log_debug(f"  Object Path: {object_path}")
                        self._log_debug(f"  Serial Number: {serial_number}")

                        # Generate and send an internal msg to DiskMsgHandler
                        self._send_msg(self.DISK_REMOVED_ALERT_TYPE, str(drive["Id"]), json.loads(json.dumps(drive)))

                        # Remove drive
                        del self._drives[object_path]

                        # Update cache with latest info
                        del self._existing_drive[object_path]
                        self._update_drive_faults()
                        store.put(self._existing_drive, self.disk_cache_path)

                # Handle jobs completed like SMART tests
                elif interface == "org.freedesktop.UDisks2.Job":
                    # If we're doing SMART tests then slow the thread down to save on CPU
                    self._thread_sleep = 1.0

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
                                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

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
        # http://udisks.freedesktop.org/docs/latest/gdbus-org.freedesktop.UDisks2.Drive.Ata.html#gdbus-property-org-freedesktop-UDisks2-Drive-Ata.SmartSelftestStatus
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

    def _send_msg(self, alert_type, resource_id, specific_info):
        """Sends an internal msg to DiskMsgHandler"""

        event_time = str(int(time.time()))
        severity_reader = SeverityReader()
        msg =  {"sensor_response_type" : "node_disk",
               "response" : {
                    "alert_type": alert_type,
                    "severity": severity_reader.map_severity(alert_type),
                    "alert_id": self._get_alert_id(event_time),
                    "host_id": socket.getfqdn(),
                    "info": {
                        "site_id": self._site_id,
                        "rack_id": self._rack_id,
                        "node_id": self._node_id,
                        "cluster_id": self._cluster_id,
                        "resource_type": self.NODE_DISK_RESOURCE_TYPE,
                        "resource_id": resource_id,
                        "event_time": event_time},
                    "specific_info": specific_info
                    }
                }
        # Send the event to disk message handler to generate json message
        self._write_internal_msgQ(DiskMsgHandler.name(), msg)

    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
           epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

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
        smart_interval = int(self._conf_reader._get_value_with_default(self.SYSTEMDWATCHDOG,
                                                         self.SMART_TEST_INTERVAL,
                                                         86400))
        # Add a sanity check to avoid constant looping, 15 minute minimum (900 secs)
        if smart_interval < 900:
            smart_interval = 86400
        return smart_interval

    def _can_run_smart_on_start(self):
        """Retrieves value of "run_smart_on_start" from configuration file.Returns
           True|False based on that.
        """
        run_smart_on_start = self._conf_reader._get_value_with_default(self.SYSTEMDWATCHDOG,
                                                         self.SMART_ON_START,
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
        smart_interval = int(self._conf_reader._get_value_with_default(self.SYSTEMDWATCHDOG,
                                                         self.SMART_SHORT_ENABLED,
                                                         86400))
        return smart_interval

    def _getConveyance_SMART_enabled(self):
        """Retrieves the flag indicating to run conveyance tests when a disk is inserted"""
        smart_interval = int(self._conf_reader._get_value_with_default(self.SYSTEMDWATCHDOG,
                                                         self.SMART_CONVEYANCE_ENABLED,
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
        result = self._run_command("sudo facter is_virtual")
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
            if not self._existing_drive[object_path] and self._is_drive_faulty(object_path):
                self._existing_drive[object_path] = True
                self._drives[object_path][self.DRIVE_FAULT_ATTR] = self._get_drive_fault_info(object_path)
                self._send_msg(self.DISK_FAULT_ALERT_TYPE,
                               str(self._drives[object_path][self.DRIVE_DBUS_INFO]["Id"]),
                               {"health_status": self._drives[object_path][self.DRIVE_FAULT_ATTR]})
            elif self._existing_drive[object_path] and not self._is_drive_faulty(object_path):
                self._existing_drive[object_path] = False
                del self._drives[object_path][self.DRIVE_FAULT_ATTR]
                self._send_msg(self.DISK_FAULT_RESOLVED_ALERT_TYPE,
                               str(self._drives[object_path][self.DRIVE_DBUS_INFO]["Id"]),
                               {"health_status": self._get_drive_fault_info(object_path)})
            # else no change


    def _is_drive_faulty(self, path):
        cmd = f"sudo smartctl -H {self._drive_by_device_name[path]}"
        response, _ = self._run_command(cmd)
        return not self.SMARTCTL_PASSED_RESPONSE in response

    def _get_drive_fault_info(self, path):
        cmd = f"sudo smartctl -A {self._drive_by_device_name[path]}"
        response, _ = self._run_command(cmd)
        return response

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(SystemdWatchdog, self).shutdown()
