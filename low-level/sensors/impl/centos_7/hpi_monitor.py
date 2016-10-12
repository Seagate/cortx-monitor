"""
 ****************************************************************************
 Filename:          hpi_monitor.py
 Description:       Monitors a specified Centos 7 path for changes
                    and notifies the disk message handler of events
 Creation Date:     07/07/2015
 Author:            Alex Cordero <alexander.cordero@seagate.com>
                    Jake Abernathy <aden.j.abernathy@seagate.com>

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os
import json
import shutil
import Queue
import time
import pyinotify
import subprocess

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from message_handlers.disk_msg_handler import DiskMsgHandler
from message_handlers.service_msg_handler import ServiceMsgHandler

from zope.interface import implements 
from sensors.IHpi_monitor import IHPIMonitor


class HPIMonitor(ScheduledModuleThread, InternalMsgQ):

    implements(IHPIMonitor)


    SENSOR_NAME       = "HPIMonitor"
    PRIORITY          = 1

    # Section and keys in configuration file
    HPIMONITOR      = SENSOR_NAME.upper()
    HPI_MONITOR_DIR = 'hpimonitor_dir'
    START_DELAY     = 'start_delay'

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return HPIMonitor.SENSOR_NAME

    def __init__(self):
        super(HPIMonitor, self).__init__(self.SENSOR_NAME,
                                                  self.PRIORITY)
        # Mapping of drives and their status'
        self._drive_data = {}

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(HPIMonitor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(HPIMonitor, self).initialize_msgQ(msgQlist)
            
        self._hpi_mntr_base_dir  = self._getHpi_Monitor_Dir()
        self._start_delay        = self._getStart_delay()

    def read_data(self):
        """Send a dict of drive status to the DiskMsgHandler"""

        for drive_data in self._drive_data:
            logger.info("HPIMonitor, read_data: %s" % str(drive_data))

            # Send it to the disk message handler to be processed and transmitted
            self._write_internal_msgQ(DiskMsgHandler.name(), drive_data)

    def run(self):
        """Run the monitoring periodically on its own thread."""

        self._log_debug("Running HPIMONITOR")

        # Allow time for the openhpid service to come up and populate /tmp/dcs/hpi
        time.sleep(40)

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        self._log_debug("Start accepting requests")
        self._log_debug("run, CentOS 7 base directory: %s" % self._hpi_mntr_base_dir)

        # Retrieve the current information about each drive from the file system
        self._init_drive_data()

        self._set_debug(True)
        self._set_debug_persist(True)

        try:
            # Followed tutorial for pyinotify: https://github.com/seb-m/pyinotify/wiki/Tutorial
            wm      = pyinotify.WatchManager()

            # Mask events to watch for on the file system
            mask    = pyinotify.IN_CLOSE_WRITE

            # Event handler class called by pyinotify when an events occurs on the file system
            handler = self.InotifyEventHandlerDef()

            # Create the blocking notifier utilizing Linux built-in inotify functionality
            self._blocking_notifier = pyinotify.Notifier(wm, handler)

            # main config method: mask is what we want to look for
            #                     rec=True, recursive thru all sub-directories
            #                     auto_add=True, automatically watch new directories
            wm.add_watch(self._hpi_mntr_base_dir, mask, rec=True, auto_add=True)

            # Loop forever blocking on this thread, monitoring file system
            #  and firing events to InotifyEventHandler: process_IN_CLOSE_WRITE()
            self._blocking_notifier.loop()

        except Exception as ae:
            # Check for debug mode being activated when it breaks out of blocking loop
            self._read_my_msgQ_noWait()

            if self.is_running() == True:
                self._log_debug("HPIMonitor ungracefully breaking " \
                                "out of iNotify Loop, restarting: %r" % ae)
                self._scheduler.enter(1, self._priority, self.run, ())
            else:
                self._log_debug("HPIMonitor gracefully breaking out " \
                                "of iNotify Loop, not restarting.")


        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        self._log_debug("Finished processing successfully")

    def _init_drive_data(self):
        """Initialize the dict containing HPI data for each disk"""

        # Wait for the dcs-collector to populate the /tmp/dcs/hpi directory
        while not os.path.isdir(self._hpi_mntr_base_dir):
            logger.info("HPIMonitor, dir not found: %s " % self._hpi_mntr_base_dir)
            logger.info("HPIMonitor, rechecking in %s secs" % self._start_delay)
            time.sleep(int(self._start_delay))

        enclosures = os.listdir(self._hpi_mntr_base_dir)

        # Remove the 'discovery' file and any others, only care about enclosure dirs
        for enclosure in enclosures:
            if not os.path.isdir(os.path.join(self._hpi_mntr_base_dir, enclosure)):
                enclosures.remove(enclosure)

        for enclosure in enclosures:
            disk_dir = os.path.join(self._hpi_mntr_base_dir, enclosure, "disk")
            self._log_debug("initializing: %s" % disk_dir)

            disks = os.listdir(disk_dir)
            for disk in disks:
                # Create the drive location path
                driveloc = os.path.join(disk_dir, disk)

                # Ignore the discovery file
                if not os.path.isdir(driveloc):
                    continue

                # Check to see if the drive is present
                serial_number = self._gather_data(driveloc+"/serial_number")

                # Update the status to status_reason used throughout
                if self._gather_data(driveloc+"/status") == "available":
                    status = "OK_None"
                else:
                    status = "EMPTY_None"

                if self._gather_data(driveloc+"/disk_installed") == "1":
                    disk_installed = True
                else:
                    disk_installed = False
            
                if self._gather_data(driveloc+"/disk_powered") == "1":
                    disk_powered = True
                else:
                    disk_powered = False

                # Read in the date for each disk and fill into dict
                json_data = {"sensor_response_type" : "disk_status_hpi",
                            "event_path"        : driveloc[len(self._hpi_mntr_base_dir)+1:],
                            "status"            : status,
                            "drawer"            : self._gather_data(driveloc+"/drawer"),
                            "location"          : self._gather_data(driveloc+"/location"),
                            "manufacturer"      : self._gather_data(driveloc+"/manufacturer"),
                            "productName"       : self._gather_data(driveloc+"/product_name"),
                            "productVersion"    : self._gather_data(driveloc+"/product_version"),
                            "serial_number"     : serial_number,
                            "wwn"               : self._gather_data(driveloc+"/wwn"),
                            "disk_installed"    : disk_installed,
                            "disk_powered"      : disk_powered
                        }

                logger.info("HPIMonitor: %s" % str(json_data))
                # Store the JSON data into the dict for global access
                self._drive_data[driveloc] = json_data

                # Send it out to initialize anyone listening
                self._write_internal_msgQ(DiskMsgHandler.name(), json_data)

        logger.info("HPIMonitor, initialization completed")

    def _gather_data(self, file):
        """Reads the data from the file and returns it as a string"""
        if not os.path.isfile(file):
            return str(None)

        with open (file, "r") as datafile:
            return str(datafile.read().replace('\n', ''))

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()
 
        return response.rstrip('\n'), error.rstrip('\n')

    def _notify_DiskMsgHandler(self, updated_file):
        """Send the event to the disk message handler for generating JSON message"""
        if not os.path.isfile(updated_file):
            logger.warn("updated_file: %s does not exist, ignoring." % updated_file)
            return

        # Parse out the drive location without the ending filename that changed
        driveloc = os.path.dirname(updated_file)

        # Check to see if the drive is present
        serial_number = self._gather_data(driveloc+"/serial_number")

        # Update the status to status_reason used throughout
        if self._gather_data(driveloc+"/status") == "available":
            status = "OK_None"
        else:
            status = "EMPTY_None"

        if self._gather_data(driveloc+"/disk_installed") == "1":
            disk_installed = True
        else:
            disk_installed = False
            
        if self._gather_data(driveloc+"/disk_powered") == "1":
            disk_powered = True
        else:
            disk_powered = False

        # Send a message to the disk message handler to transmit
        json_data = {"sensor_response_type" : "disk_status_hpi",
                     "event_path"           : driveloc[len(self._hpi_mntr_base_dir)+1:],
                     "status"               : status,
                     "drawer"               : self._gather_data(driveloc+"/drawer"),
                     "location"             : self._gather_data(driveloc+"/location"),
                     "manufacturer"         : self._gather_data(driveloc+"/manufacturer"),
                     "productName"          : self._gather_data(driveloc+"/product_name"),
                     "productVersion"       : self._gather_data(driveloc+"/product_version"),
                     "serial_number"        : serial_number,
                     "wwn"                  : self._gather_data(driveloc+"/wwn"),
                     "disk_installed"       : disk_installed,
                     "disk_powered"         : disk_powered
                     }

        # Do nothing if the overall state has not changed anywhere
        if self._drive_data.get(driveloc) is not None and \
            self._drive_data.get(driveloc) == json_data:
            return

        # Store the JSON data into the dict for global access
        self._drive_data[driveloc] = json_data

        # Send the event to disk message handler to generate json message
        self._write_internal_msgQ(DiskMsgHandler.name(), json_data)

        # Restart openhpid to update HPI data for newly installed drives
        if serial_number == "ZBX_NOTPRESENT" and \
           disk_installed == True and \
           disk_powered == True:
                logger.info("HPImonitor, _notify_DiskMsgHandler, Restarting openhpid")
                time.sleep(20)
                command = "/usr/bin/systemctl restart openhpid"
                response, error = self._run_command(command)
                if len(error) > 0:
                    logger.info("Error restarting openhpid: %s" % error)
                else:
                    logger.info("Restarted openhpid succesfully")

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

    def InotifyEventHandlerDef(self):
        """Internal event handling class for Inotify"""
        _parent = self

        class InotifyEventHandler(pyinotify.ProcessEvent):

            def process_IN_CLOSE_WRITE(self, event):
                """Callback method from inotify when a file has been written and closed"""
                # Check for debug mode being activated from external JSON msg
                _parent._read_my_msgQ_noWait()

                # Validate the event path; must have disk and be a status/drawer file and not be a swap file
                if self._validate_event_path(event.pathname):
                    #self._log_debug("InotifyEventHandler, process_IN_CLOSE_WRITE, event: %s" % event)
                    status_file = os.path.join(os.path.dirname(event.pathname), "status")
                    _parent._notify_DiskMsgHandler(status_file)

            def _validate_event_path(self, event_path):
                """Returns true if the event path is valid for a status file"""

                 # Validate the event path; must be one of the following and not be a swap file
                if "disk" not in event_path or \
                    (("serial_number" not in event_path or \
                    "serial_number.swp" in event_path) and \
                    ("disk_powered" not in event_path or \
                    "disk_powered.swp" in event_path) and \
                    ("disk_installed" not in event_path or \
                    "disk_installed.swp" in event_path)):
                    return False

                self._log_debug("_validate_event_path event_path: %s" %
                        event_path)
                return True

            def _log_debug(self, msg):
                """Used to log debug messages from within this inner class, if needed"""
                if _parent._get_debug() == True:
                    logger.info(msg)

        iNotifyEventHandler = InotifyEventHandler()
        return iNotifyEventHandler

    def _getHpi_Monitor_Dir(self):
        """Retrieves the hpi monitor path to monitor on the file system"""
        return self._conf_reader._get_value_with_default(self.HPIMONITOR,
                                                         self.HPI_MONITOR_DIR,
                                                         '/tmp/dcs/hpi')

    def _getStart_delay(self):
        """Retrieves the start delay used to allow dcs-collector to startup first"""
        return self._conf_reader._get_value_with_default(self.HPIMONITOR,
                                                         self.START_DELAY,
                                                         '20')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(HPIMonitor, self).shutdown()
        try:
            self._blocking_notifier.stop()
        except Exception:
            logger.info("HPIMonitor, shutting down.")
