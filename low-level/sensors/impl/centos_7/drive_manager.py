"""
 ****************************************************************************
 Filename:          drive_manager.py
 Description:       Monitors a specified Centos 7 path for changes
                    and notifies the disk message handler of events
 Creation Date:     01/14/2015
 Author:            Jake Abernathy

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
import pyinotify

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from message_handlers.disk_msg_handler import DiskMsgHandler
from json_msgs.messages.sensors.drive_mngr import DriveMngrMsg

from zope.interface import implements
from sensors.IDrive_manager import IDriveManager


class DriveManager(ScheduledModuleThread, InternalMsgQ):

    implements(IDriveManager)

    MODULE_NAME       = "DriveManager"
    PRIORITY          = 1

    # Section and keys in configuration file
    DRIVEMANAGER      = MODULE_NAME.upper()
    DRIVE_MANAGER_DIR = 'drivemanager_dir'
    DRIVE_MANAGER_PID = 'drivemanager_pid'


    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return DriveManager.MODULE_NAME

    def __init__(self):
        super(DriveManager, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)       
        # Mapping of drives and their status'
        self._drive_status = {}

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(DriveManager, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(DriveManager, self).initialize_msgQ(msgQlist)

        self._drive_mngr_base_dir  = self._getDrive_Mngr_Dir()
        self._drive_mngr_pid       = self._getDrive_Mngr_Pid()

    def read_data(self):
        """Return the dict of drive status'"""
        return self._drive_status

    def run(self):
        """Run the monitoring periodically on its own thread."""
        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        #self._set_debug(True)
        #self._set_debug_persist(True)

        self._log_debug("Start accepting requests")
        self._log_debug("run, CentOS 7 base directory: %s" % self._drive_mngr_base_dir)

        # Retrieve the current information about each drive from the file system
        self._init_drive_status()

        try:
            # Followed tutorial for pyinotify: https://github.com/seb-m/pyinotify/wiki/Tutorial
            wm      = pyinotify.WatchManager()

            # Mask events to watch for on the file system
            mask    = pyinotify.IN_CLOSE_WRITE | pyinotify.IN_CREATE | pyinotify.IN_DELETE

            # Event handler class called by pyinotify when an events occurs on the file system
            handler = self.InotifyEventHandlerDef()

            # Create the blocking notifier utilizing Linux built-in inotify functionality
            self._blocking_notifier = pyinotify.Notifier(wm, handler)

            # main config method: mask is what we want to look for
            #                     rec=True, recursive thru all sub-directories
            #                     auto_add=True, automatically watch new directories
            wm.add_watch(self._drive_mngr_base_dir, mask, rec=True, auto_add=True)                   

            # Loop forever blocking on this thread, monitoring file system 
            #  and firing events to InotifyEventHandler: process_IN_CREATE(), process_IN_DELETE()            
            self._blocking_notifier.loop()

        except Exception as ae:
            # Check for debug mode being activated when it breaks out of blocking loop
            self._read_my_msgQ_noWait()
            if self.is_running() == True:
                self._log_debug("DriveManager ungracefully breaking " \
                                "out of iNotify Loop, restarting: %r" % ae)
                self._scheduler.enter(1, self._priority, self.run, ())
            else:
                self._log_debug("DriveManager gracefully breaking out " \
                                "of iNotify Loop, not restarting.")

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        self._log_debug("Finished processing successfully")

    def _init_drive_status(self):
        enclosures = os.listdir(self._drive_mngr_base_dir)
        for enclosure in enclosures:
            disk_dir = os.path.join(self._drive_mngr_base_dir, enclosure, "disk")
            disks = os.listdir(disk_dir)
            logger.info("DriveManager initializing: %s" % disk_dir)

            for disk in disks:
                # Read in the status file for each disk and fill into dict
                pathname = os.path.join(disk_dir, disk)
                status_file = os.path.join(pathname, "status")
                if not os.path.isfile(status_file):
                    continue
                try:
                    with open (status_file, "r") as datafile:
                        status = datafile.read().replace('\n', '')
                        logger.info("DriveManager, pathname: %s, status: %s" % 
                                    (pathname, status))
                        self._drive_status[pathname] = status
                except Exception as e:
                    logger.info("DriveManager, _init_drive_status, exception: %s" % e)

    def _getDrive_Mngr_Dir(self):
        """Retrieves the drivemanager path to monitor on the file system"""
        return self._conf_reader._get_value_with_default(self.DRIVEMANAGER, 
                                                                 self.DRIVE_MANAGER_DIR,
                                                                 '/tmp/dcs/drivemanager')                
    def _getDrive_Mngr_Pid(self):
        """Retrieves the pid file indicating pyinotify is running or not"""
        return self._conf_reader._get_value_with_default(self.DRIVEMANAGER,
                                                                 self.DRIVE_MANAGER_PID,
                                                                 '/var/run/pyinotify.pid')
    def _notify_DiskMsgHandler(self, status_file):
        """Send the event to the disk message handler for generating JSON message"""

        if not os.path.isfile(status_file):
            logger.warn("status_file: %s does not exist, ignoring." % status_file)
            return

        # Read in status and see if it has changed
        with open (status_file, "r") as datafile:
            status = datafile.read().replace('\n', '')
 
        # Do nothing if the drive status has not changed
        if self._drive_status[os.path.dirname(status_file)] == status:
            return

        # Update the status for this drive
        self._log_debug("Status change, status_file: %s, status: %s" % (status_file, status))
        self._drive_status[os.path.dirname(status_file)] = status

        # Remove base dcs dir since it contains no relevant data
        data_str = status_file[len(self._drive_mngr_base_dir)+1:]

        # Send a message to the disk manager handler to create and transmit json msg
        internal_json_msg = json.dumps( 
            {"sensor_response_type" : "disk_status_drivemanager",
                "event_path" : data_str,
                "status" : status
            })

        # Send the event to disk message handler to generate json message
        self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

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
                    "status" not in event_path or \
                    "status.swp" in event_path:
                    return False

                return True

            def _log_debug(self, msg):
                """Used to log debug messages from within this inner class, if needed"""
                if _parent._get_debug() == True:
                    logger.info(msg)

        iNotifyEventHandler = InotifyEventHandler()
        return iNotifyEventHandler

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DriveManager, self).shutdown()
        try:            
            self._log_debug("DriveManager, shutdown: removing pid:%s" % self._drive_mngr_pid)     
            if os.path.isfile(self._drive_mngr_pid):
                os.remove(self._drive_mngr_pid)
            self._blocking_notifier.stop()

        except Exception:
            logger.info("DriveManager, shutting down.")
    