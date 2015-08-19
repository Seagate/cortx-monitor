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

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from message_handlers.disk_msg_handler import DiskMsgHandler

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
        # Allow time for the dcs-collector to come up and populate the directory
        time.sleep(10)

        # Allow time for the dcs-collector to come up and populate the directory
        while not os.path.isdir(self._hpi_mntr_base_dir):
            logger.info("HPIMonitor, dir not found: %s " % self._hpi_mntr_base_dir)
            logger.info("HPIMonitor, rechecking in %s secs" % self._start_delay)
            time.sleep(int(self._start_delay))

        enclosures = os.listdir(self._hpi_mntr_base_dir)
        # Remove the 'discovery' file
        for enclosure in enclosures:
            if not os.path.isdir(os.path.join(self._hpi_mntr_base_dir, enclosure)):
                enclosures.remove(enclosure)

        for enclosure in enclosures:
            disk_dir = os.path.join(self._hpi_mntr_base_dir, enclosure, "disk")
            self._log_debug("initializing: %s" % disk_dir)

            disks = os.listdir(disk_dir)
            for disk in disks:
                # Read in the serial_number file for each disk and fill into dict
                driveloc = os.path.join(disk_dir, disk)

                # Ignore the discovery file
                if not os.path.isdir(driveloc):
                    continue

                json_data = {"sensor_response_type" : "disk_status_hpi",
                            "event_path"        : driveloc[len(self._hpi_mntr_base_dir)+1:],
                            "status"            : self._gather_data(driveloc+"/status"),
                            "drawer"            : self._gather_data(driveloc+"/drawer"),
                            "location"          : self._gather_data(driveloc+"/location"),
                            "manufacturer"      : self._gather_data(driveloc+"/manufacturer"),
                            "productName"       : self._gather_data(driveloc+"/product_name"),
                            "productVersion"    : self._gather_data(driveloc+"/product_version"),
                            "serialNumber"      : self._gather_data(driveloc+"/serial_number"),
                            "wwn"               : self._gather_data(driveloc+"/wwn")
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

    def _notify_DiskMsgHandler(self, updated_file):
        """Send the event to the disk message handler for generating JSON message"""
        if not os.path.isfile(updated_file):
            logger.warn("updated_file: %s does not exist, ignoring." % updated_file)
            return

        # Parse out the drive location without the ending filename that changed
        driveloc = os.path.dirname(updated_file)
        self._log_debug("_notify_DiskMsgHandler updated_file: %s, driveloc: %s" % 
                        (updated_file, driveloc))

        # Send a message to the disk message handler to transmit
        json_data = {"sensor_response_type" : "disk_status_hpi",
                     "event_path"           : driveloc[len(self._hpi_mntr_base_dir)+1:],
                     "status"               : self._gather_data(driveloc+"/status"),
                     "drawer"               : self._gather_data(driveloc+"/drawer"),
                     "location"             : self._gather_data(driveloc+"/location"),
                     "manufacturer"         : self._gather_data(driveloc+"/manufacturer"),
                     "productName"          : self._gather_data(driveloc+"/product_name"),
                     "productVersion"       : self._gather_data(driveloc+"/product_version"),
                     "serialNumber"         : self._gather_data(driveloc+"/serial_number"),
                     "wwn"                  : self._gather_data(driveloc+"/wwn")
                     }

        # Do nothing if the overall state has not changed anywhere
        if self._drive_data[driveloc] == json_data:
            return

        # Store the JSON data into the dict for global access
        self._drive_data[driveloc] = json_data

        # Send the event to disk message handler to generate json message
        self._write_internal_msgQ(DiskMsgHandler.name(), json_data)

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

                 # Validate the event path; must have disk and be a status and not be a swap file
                if "disk" not in event_path or \
                    (("status" not in event_path or \
                    "status.swp" in event_path) and  \
                    ("drawer" not in event_path or \
                    "drawer.swp" in event_path) and \
                    ("location" not in event_path or \
                    "location.swp" in event_path) and \
                    ("manufacturer" not in event_path or \
                    "manufacturer.swp" in event_path) and \
                    ("product_name" not in event_path or \
                    "product_name.swp" in event_path) and \
                    ("product_version" not in event_path or \
                    "product_version.swp" in event_path) and \
                    ("serial_number" not in event_path or \
                    "serial_number.swp" in event_path) and \
                    ("wwn" not in event_path or \
                    "wwn.swp" in event_path)):
                    return False

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
