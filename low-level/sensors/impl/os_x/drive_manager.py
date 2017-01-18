"""
 ****************************************************************************
 Filename:          drive_manager.py
 Description:       Monitors a specified Mac OS X path for changes
                    and notifies the disk message handler of events.
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

from zope.interface import implements
from sensors.IDrive_manager import IDriveManager


class DriveManager(ScheduledModuleThread, InternalMsgQ):

    implements(IDriveManager)

    SENSOR_NAME       = "DriveManager"
    PRIORITY          = 2

    # Section and keys in configuration file
    DRIVEMANAGER        = SENSOR_NAME.upper()
    DRIVE_MANAGER_DIR   = 'drivemanager_dir'

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return DriveManager.SENSOR_NAME

    def __init__(self):
        super(DriveManager, self).__init__(self.SENSOR_NAME,
                                           self.PRIORITY)
        # Mapping of drives and their status'
        self._drive_status = {}

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(DriveManager, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(DriveManager, self).initialize_msgQ(msgQlist)

        self._drive_mngr_base_dir  = self._getDrive_Mngr_Dir()

    def read_data(self):
        """Return the dict of drive status'"""
        return self._drive_status

    def run(self):
        """Run the monitoring periodically on its own thread."""
        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        self._log_debug("Start accepting requests")
        self._log_debug("run, MAC OS X base directory: %s" % self._drive_mngr_base_dir)


        # Code to handle MAC OS X drive manager events here...



    def _getDrive_Mngr_Dir(self):
        """Retrieves the drivemanager path to monitor on the file system"""
        return self._conf_reader._get_value_with_default(self.DRIVEMANAGER,
                                                         self.DRIVE_MANAGER_DIR,
                                                         '/tmp/dcs/drivemanager')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DriveManager, self).shutdown()
#         try:
#             self._blocking_notifier.stop()
#         except Exception:
#             logger.info("DriveManager, shutting down.")