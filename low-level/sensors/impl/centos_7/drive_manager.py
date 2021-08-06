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
  Description:       Monitors a specified Centos 7 path for changes
                    and notifies the disk message handler of events
 ****************************************************************************

         This Sensor Has Been Deprecated by the Systemd Watchdog
         02/01/2016 Jake Abernathy

"""

import json
import os
import subprocess
import time

import pyinotify
from zope.interface import implementer

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from framework.base.sspl_constants import PRODUCT_FAMILY
from framework.utils.conf_utils import SSPL_CONF, Conf
from framework.utils.service_logging import logger
# Modules that receive messages from this module
from message_handlers.disk_msg_handler import DiskMsgHandler
from sensors.IDrive_manager import IDriveManager


@implementer(IDriveManager)
class DriveManager(SensorThread, InternalMsgQ):

    SENSOR_NAME     = "DriveManager"
    PRIORITY        = 1

    # Section and keys in configuration file
    DRIVEMANAGER      = SENSOR_NAME.upper()
    DRIVE_MANAGER_DIR = 'drivemanager_dir'
    START_DELAY       = 'start_delay'


    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return DriveManager.SENSOR_NAME

    @staticmethod
    def impact():
        """Returns impact of the module."""
        return ("Drive path changes can not be monitored "
                "on storage enclosure and server.")

    def __init__(self):
        super(DriveManager, self).__init__(self.SENSOR_NAME,
                                                  self.PRIORITY)
        # Mapping of drives and their status'
        self._drive_status = {}

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(DriveManager, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(DriveManager, self).initialize_msgQ(msgQlist)

        self._drive_status : Dict[str, str] = {}

        self._drive_mngr_base_dir  = self._getDrive_Mngr_Dir()
        self._start_delay          = self._getStart_delay()

        return True

    def read_data(self):
        """Return the dict of drive status'"""
        return self._drive_status

    def run(self):
        """Run the monitoring periodically on its own thread."""
        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        self._log_debug("Start accepting requests")
        self._log_debug(f"run, CentOS 7 base directory: {self._drive_mngr_base_dir}")

        # Retrieve the current information about each drive from the file system
        self._init_drive_status()

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
            wm.add_watch(self._drive_mngr_base_dir, mask, rec=True, auto_add=True)

            # Loop forever blocking on this thread, monitoring file system
            #  and firing events to InotifyEventHandler: process_IN_CLOSE_WRITE()
            self._blocking_notifier.loop()

        except Exception as ae:
            # Check for debug mode being activated when it breaks out of blocking loop
            self._read_my_msgQ_noWait()
            if self.is_running() is True:
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
        # Allow time for the drivemanager to come up and populate the directory
        time.sleep(5)

        # Ensure there are enclosures present
        self._validate_drive_manager_dir()

        enclosures = os.listdir(self._drive_mngr_base_dir)
        # Remove the 'discovery' file
        enclosures = [enclosure for enclosure in enclosures \
                 if not os.path.isdir(os.path.join(self._drive_mngr_base_dir, enclosure))]

        for enclosure in enclosures:
            disk_dir = os.path.join(self._drive_mngr_base_dir, enclosure, "disk")
            logger.info(f"DriveManager initializing: {disk_dir}")

            disks = os.listdir(disk_dir)
            for disk in disks:
                # Read in the status file for each disk and fill into dict
                pathname = os.path.join(disk_dir, disk)
                # Ignore the discovery file
                if not os.path.isdir(pathname):
                    continue

                # Read in the serial number for the disk
                serial_num_file = os.path.join(pathname, "serial_number")
                if not os.path.isfile(serial_num_file):
                    logger.error(f"DriveManager error no serial_number file for disk: {disk}")
                    continue
                try:
                    with open(serial_num_file, "r") as datafile:
                        serial_number = datafile.read().replace('\n', '')
                except Exception as e:
                    logger.info(f"DriveManager, _init_drive_status, exception: {e}")

                # Read in the status for the disk
                status_file = os.path.join(pathname, "status")
                if not os.path.isfile(status_file):
                    logger.error(f"DriveManager error no status file for disk: {disk}")
                    continue
                try:
                    with open(status_file, "r") as datafile:
                        status = datafile.read().replace('\n', '')

                    # Read in the reason file if it's present
                    reason_file = os.path.join(pathname, "reason")

                    if os.path.isfile(reason_file):
                        with open(reason_file, "r") as datafile:
                            reason = datafile.read().replace('\n', '')

                        # Append the reason to the status file
                        self._drive_status[pathname] = f"{status}_{reason}"
                    else:
                        self._drive_status[pathname] = status

                    logger.info(f"DriveManager, pathname: {pathname}, status: {self._drive_status[pathname]}")

                    # Remove base dcs dir since it contains no relevant data
                    data_str = status_file[len(self._drive_mngr_base_dir)+1:]

                    # Send a message to the disk manager handler to create and transmit json msg
                    internal_json_msg = json.dumps(
                        {"sensor_response_type" : "disk_status_drivemanager",
                         "event_path" : data_str,
                         "status" : self._drive_status[pathname],
                         "serial_number" : serial_number
                         })

                    # Send the event to disk message handler to generate json message
                    self._write_internal_msgQ(DiskMsgHandler.name(), internal_json_msg)

                except Exception as e:
                    logger.info(f"DriveManager, _init_drive_status, exception: {e}")

            logger.info("DriveManager, initialization completed")

    def _validate_drive_manager_dir(self):
        """Loops until the base dir is populated with enclosures by dcs-collector"""
        while not os.path.isdir(self._drive_mngr_base_dir):
            logger.info(f"DriveManager sensor, dir not found: {self._drive_mngr_base_dir}")
            logger.info(f"DriveManager sensor, rechecking in {self._start_delay} secs")
            time.sleep(int(self._start_delay))

        enclosures = os.listdir(self._drive_mngr_base_dir)
        # Remove the 'discovery' file
        for enclosure in enclosures:
            if not os.path.isdir(os.path.join(self._drive_mngr_base_dir, enclosure)):
                enclosures.remove(enclosure)

        while not enclosures:
           logger.info(f"DriveManager sensor, no enclosures found: {self._drive_mngr_base_dir}")
           logger.info(f"DriveManager sensor, rechecking in {(int(self._start_delay))} secs")

           # Attempt to initialize gemhpi
           command = f"sudo /opt/seagate/{PRODUCT_FAMILY}/sspl/low-level/framework/init_gemhpi"
           process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
           response, error = process.communicate()
           logger.info(f"DriveManager sensor, initializing gem, result: {response}, error: {error}")

           time.sleep(int(self._start_delay))
           enclosures = os.listdir(self._drive_mngr_base_dir)
           for enclosure in enclosures:
               if not os.path.isdir(os.path.join(self._drive_mngr_base_dir, enclosure)):
                   enclosures.remove(enclosure)

    def _getDrive_Mngr_Dir(self):
        """Retrieves the drivemanager path to monitor on the file system"""
        return Conf.get(SSPL_CONF, f"{self.DRIVEMANAGER}>{self.DRIVE_MANAGER_DIR}",
                                                    '/tmp/dcs/drivemanager')

    def _getStart_delay(self):
        """Retrieves the start delay used to allow dcs-collector to startup first"""
        return Conf.get(SSPL_CONF, f"{self.DRIVEMANAGER}>{self.START_DELAY}",
                                                    '20')

    def _notify_DiskMsgHandler(self, status_file : str, serial_num_file):
        """Send the event to the disk message handler for generating JSON message"""

        if not os.path.isfile(status_file):
            logger.warn(f"status_file: {status_file} does not exist, ignoring.")
            return

        if not os.path.isfile(serial_num_file):
            logger.warn(f"serial_num_file: {serial_num_file} does not exist, ignoring.")
            return

        # Read in status and see if it has changed
        with open (status_file, "r") as datafile:
            status = datafile.read().replace('\n', '')

        # See if there's a reason file
        reason_file = os.path.join (os.path.dirname(status_file), "reason")
        if os.path.isfile(reason_file):
            with open(reason_file, "r") as datafile:
                reason = datafile.read().replace('\n', '')
                status = f"{status}_{reason}"

        # Do nothing if the drive status has not changed
        if self._drive_status[os.path.dirname(status_file)] == status:
            return

        # Update the status for this drive
        self._log_debug(f"Status change, status_file: {status_file}, status: {status}")
        self._drive_status[os.path.dirname(status_file)] = status

        # Read in the serial number
        with open (serial_num_file, "r") as datafile:
            serial_number = datafile.read().replace('\n', '')

        # Remove base dcs dir since it contains no relevant data
        data_str = status_file[len(self._drive_mngr_base_dir)+1:]

        # Send a message to the disk manager handler to create and transmit json msg
        internal_json_msg = json.dumps(
            {"sensor_response_type" : "disk_status_drivemanager",
                "event_path" : data_str,
                "status" : status,
                "serial_number" : serial_number
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
                    serial_num_file = os.path.join(os.path.dirname(event.pathname), "serial_number")
                    _parent._notify_DiskMsgHandler(status_file, serial_num_file)

            def _validate_event_path(self, event_path):
                """Returns true if the event path is valid for a status file"""

                 # Validate the event path; must have disk and be a status or reason and not be a swap file
                if "disk" not in event_path or \
                    (("status" not in event_path or \
                    "status.swp" in event_path) and  \
                    ("reason" not in event_path or \
                    "reason.swp" in event_path)):
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
            self._blocking_notifier.stop()
        except Exception:
            logger.info("DriveManager, shutting down.")
