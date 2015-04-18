"""
 ****************************************************************************
 Filename:          disk_msg_handler.py
 Description:       Message Handler for Disk Sensor Messages
 Creation Date:     02/25/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
import syslog

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

from json_msgs.messages.sensors.drive_mngr import DriveMngrMsg


class DiskMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for Disk Sensor Messages"""

    MODULE_NAME = "DiskMsgHandler"
    PRIORITY    = 2

    # Section and keys in configuration file
    DISKMSGHANDLER = MODULE_NAME.upper()


    @staticmethod
    def name():
        """ @return: name of the module."""
        return DiskMsgHandler.MODULE_NAME

    def __init__(self):
        super(DiskMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(DiskMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(DiskMsgHandler, self).initialize_msgQ(msgQlist)

    def run(self):
        """Run the module periodically on its own thread."""

        #self._set_debug(True)
        #self._set_debug_persist(True)

        self._log_debug("Start accepting requests")

        try:
            # Block on message queue until it contains an entry
            jsonMsg = self._read_my_msgQ()
            if jsonMsg is not None:
                self._process_msg(jsonMsg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                jsonMsg = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._process_msg(jsonMsg)

        except Exception:
            # Log it and restart the whole process when a failure occurs
            logger.exception("DiskMsgHandler restarting")

        self._scheduler.enter(0, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger"""    
        self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)  

        if isinstance(jsonMsg, dict) == False:
            jsonMsg = json.loads(jsonMsg)

        if jsonMsg.get("sensor_response_type") is not None:
            self._log_debug("_processMsg, msg_type: disk_status_drivemanager")

            # Convert event path to Drive object to handle parsing and json conversion, etc
            event_path = jsonMsg.get("event_path")
            status     = jsonMsg.get("status")
            drive = Drive(event_path, status)

            # Check to see if the drive path is valid
            valid = drive.parse_path()

            self._log_debug("_process_msg enclosureSN: %s" % drive.get_drive_enclosure() \
                            + ", diskNum: %s" % drive.get_drive_num() \
                            + ", filename: %s"  % drive.get_drive_filename() \
                            + ", diskStatus: %s"  % drive.get_drive_status())      

            if not valid:
                self._log_debug("_process_msg, valid: False (ignoring)")
                return

            # Obtain json message containing all relevant data
            internal_json_msg = drive.toJsonMsg().getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._log_debug("_process_msg, internal_json_msg: %s" % internal_json_msg)
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        # ... handle other disk message types

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DiskMsgHandler, self).shutdown()


class Drive(object):
    """Object representation of a drive"""

    def __init__(self, path, status):
        super(Drive, self).__init__()
        self._path      = path
        self._status    = status
        self._enclosure = "N/A"
        self._drive_num = "N/A"        
        self._filename  = "N/A"

    def parse_path(self):
        """Parse the path of the file, return True if valid file name exists in path"""
        try:
            # Parse out enclosure and drive number
            path_values = self._path.split("/")

            # See if there is a valid filename at the end: serial_number, slot, status
            # Normal path will be: [enclosure sn]/disk/[drive number]/status
            if len(path_values) < 4:
                return False

            # Parse out values for drive
            self._enclosure = path_values[0]
            self._drive_num = path_values[2]
            self._filename  = path_values[3]

            return True

        except Exception as ex:
            logger.exception("Drive, _parse_path: %s, ignoring event." % ex)
        return False

    def toJsonMsg(self):
        """Returns the JSON representation of a drive"""
        # Create a drive manager json object which can be
        #  be queued up for aggregation at a later time if needed
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
