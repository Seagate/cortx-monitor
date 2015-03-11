"""
 ****************************************************************************
 Filename:          drive_manager_monitor.py
 Description:       Monitors the specified file system for changes,
                    creates json messages and notifies rabbitmq thread
                    to broadcast to rabbitmq topic defined in conf file
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
import Queue
import pyinotify

from framework.base.debug import Debug

from json_msgs.messages.monitors.drive_mngr import DriveMngrMsg
from framework.base.module_thread import ScheduledModuleThread 
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# List of modules that receive messages from this module
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor 


class DriveManagerMonitor(ScheduledModuleThread, InternalMsgQ):
    
    MODULE_NAME       = "DriveManagerMonitor"
    PRIORITY          = 2

    # Section and keys in configuration file
    DRIVEMANAGERMONITOR = MODULE_NAME.upper()
    DRIVE_MANAGER_DIR   = 'drivemanager_dir'
    DRIVE_MANAGER_PID   = 'drivemanager_pid'


    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return DriveManagerMonitor.MODULE_NAME

    def __init__(self):
        super(DriveManagerMonitor, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        self._sentJSONmsg = None

        # Mapping of drives and their status'
        self._drive_status = {}

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(DriveManagerMonitor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(DriveManagerMonitor, self).initialize_msgQ(msgQlist)

        self._drive_mngr_base_dir  = self._getDrive_Mngr_Dir()
        self._drive_mngr_pid       = self._getDrive_Mngr_Pid()

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DriveManagerMonitor, self).shutdown()
        try:            
            self._log_debug("DriveManagerMonitor, shutdown: removing pid:%s" % self._drive_mngr_pid)     
            if os.path.isfile(self._drive_mngr_pid):
                os.remove(self._drive_mngr_pid)
            self._blocking_notifier.stop()

        except Exception as ex:
            logger.exception("DriveManagerMonitor, shutdown: %s" % ex)

    def run(self):
        """Run the monitoring periodically on its own thread."""
        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        self._log_debug("Start accepting requests")
        self._log_debug("run, base directory: %s" % self._drive_mngr_base_dir)
        logger.info("DriveManager started, initializing drives...")

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
                self._log_debug("DriveManagerMonitor ungracefully breaking " \
                                "out of iNotify Loop, restarting: %r" % ae)
                self._scheduler.enter(1, self._priority, self.run, ())
            else:
                self._log_debug("DriveManagerMonitor gracefully breaking out " \
                                "of iNotify Loop, not restarting.")

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        self._log_debug("Finished processing successfully")

    def _getDrive_Mngr_Dir(self):
        """Retrieves the drivemanager path to monitor on the file system"""
        return self._conf_reader._get_value_with_default(self.DRIVEMANAGERMONITOR, 
                                                                 self.DRIVE_MANAGER_DIR,
                                                                 '/tmp/dcs/drivemanager')                
    def _getDrive_Mngr_Pid(self):
        """Retrieves the pid file indicating pyinotify is running or not"""
        return self._conf_reader._get_value_with_default(self.DRIVEMANAGERMONITOR, 
                                                                 self.DRIVE_MANAGER_PID,
                                                                 '/var/run/pyinotify.pid')        
    def _send_json_RabbitMQ(self, pathname, event_type):
        """Place the json message into the RabbitMQprocessor queue if valid"""
        # Convert pathname to Drive object to handle parsing and json conversion, etc
        drive = Drive(pathname, self._drive_mngr_base_dir)

        # Check to see if the drive path is valid
        valid = drive.parse_path()

        self._log_debug("Drive, _parse_path, _drive_enclosure: %s" % drive.get_drive_enclosure())
        self._log_debug("Drive, _parse_path, _drive_num: %s" % drive.get_drive_num())
        self._log_debug("Drive, _parse_path, _drive_filename: %s"  % drive.get_drive_filename())
        self._log_debug("Drive, _parse_path, _drive_status: %s"  % drive.get_drive_status())

        if not valid:
            self._log_debug("_send_json_RabbitMQ, valid: False (ignoring)")
            return

        # Obtain json message containing all relevant data
        jsonMsg = drive.toJsonMsg()

        # Do nothing if we're starting up and initializing the status for all drives
        if pathname not in self._drive_status:
            self._drive_status[pathname] = drive.get_drive_status()
            logger.info("Enclosure: %s, Drive Number: %s" % \
                        (drive.get_drive_enclosure(), drive.get_drive_num()))
            return

        # Do nothing if the drive status has not changed
        if self._drive_status[pathname] == drive.get_drive_status():
                return

        # Update the status for this drive
        self._drive_status[pathname] = drive.get_drive_status()

        # Sometimes iNotify sends the same event twice, catch and ignore
        msgString = jsonMsg.getJson()
        if msgString != self._sentJSONmsg:
            # Send the json message to the RabbitMQ processor to transmit out
            self._log_debug("DriveManagerMonitor, _send_json_RabbitMQ: jsonMsg: %s" % msgString)
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), msgString)
            self._sentJSONmsg = msgString

            # Reset debug mode if persistence is not enabled
            self._disable_debug_if_persist_false()

    def InotifyEventHandlerDef(self):
        """Internal event handling class for Inotify"""
        _parent = self
        
        class InotifyEventHandler(pyinotify.ProcessEvent):
            def process_IN_DELETE(self, event):
                """Callback method from inotify when a delete file event occurs"""
                # Saving this for debug purposes on real hardware; we might need to act on
                #  events where files or dirs are deleted on the fs
                self._log_debug("InotifyEventHandler, process_IN_DELETE, event: %s" % event)
                #_parent._send_json_RabbitMQ(event.pathname, "DELETE")

            def process_IN_CREATE(self, event):
                """Callback method from inotify when a create file event occurs"""
                # Saving this for debug purposes on real hardware; we might need to act on
                #  events where files or dirs are created on the fs
                self._log_debug("InotifyEventHandler, process_IN_CREATE, event: %s" % event)
                #_parent._send_json_RabbitMQ(event.pathname, "CREATE")

            def process_IN_CLOSE_WRITE(self, event):
                """Callback method from inotify when a file has been written and closed"""
                # Check for debug mode being activated from external JSON msg
                _parent._read_my_msgQ_noWait()
        
                # Validate the event path; must have disk and be a status and not be a swap file
                if self._validate_event_path(event.pathname):
                    self._log_debug("InotifyEventHandler, process_IN_CLOSE_WRITE, event: %s" % event)
                    _parent._send_json_RabbitMQ(event.pathname, "UPDATE")

            def _validate_event_path(self, event_path):
                """Returns true if the event path is valid for a status file"""
                 # Validate the event path; must have disk and be a status and not be a swap file
                if "disk" not in event_path:
                    self._log_debug("InotifyEventHandler event_path: Does not contain the required keyword 'disk'")
                elif "status" not in event_path:
                    self._log_debug("InotifyEventHandler event_path: Does not contain the required keyword 'status'")
                elif "status.swp" in event_path:
                    self._log_debug("InotifyEventHandler event_path: Ignoring swap files")
                else:
                    return True
                return False

            def _log_debug(self, msg):
                if _parent._get_debug() == True:
                    logger.info(msg)

        iNotifyEventHandler = InotifyEventHandler()
        return iNotifyEventHandler


class Drive(object):
    """Object representation of a drive"""

    def __init__(self, path, drive_mngr_base_dir):
        super(Drive, self).__init__()
        self._path = path
        self._drive_mngr_base_dir = drive_mngr_base_dir

        self._enclosure = "N/A"
        self._drive_num = "N/A"
        self._status    = "N/A"
        self._filename  = "N/A"

    def parse_path(self):
        """Parse the path of the file, return True if valid file name exists in path"""
        try:
            # Remove base dcs dir and split into list parsing out enclosure and drive num
            data_str = self._path[len(self._drive_mngr_base_dir)+1:]
            path_values = data_str.split("/")

            # See if there is a valid filename at the end: serial_number, slot, status
            # Normal path will be: enclosure/disk/drive number
            if len(path_values) < 4:
                return False

            # Parse out values for drive
            self._enclosure = path_values[0]
            self._drive_num = path_values[2]

            # Read in the value of the file at the end of the path
            self._filename  = path_values[3]

            # The drive manager status file is currently only being used.
            drive_path = self._path
            if self._filename == "status.tmp":
                drive_path = self._path[:-4]

            with open (drive_path, "r") as datafile:
                data = datafile.read().replace('\n', '')
            self._status = data

            return True

        except Exception as ex:
            logger.exception("Drive, _parse_path: %s, ignoring event." % ex)
        return False

    def toJsonMsg(self):
        """Returns the JSON representation of a drive"""
        # Create a drive manager json object which can be
        #  be queued up for aggregation at a later time.
        jsonMsg = DriveMngrMsg(self._enclosure,
                               self._drive_num,
                               self._status)
        return jsonMsg

    def get_drive_status(self):
        """Return the status of the drive"""    
        return self._status
    
    def get_drive_enclosure(self):
        """Return the enclosure of the drive"""    
        return self._enclosure
    
    def get_drive_num(self):
        """Return the enclosure of the drive"""    
        return self._drive_num
    
    def get_drive_filename(self):
        """Return the filename of the drive"""    
        return self._filename
    
