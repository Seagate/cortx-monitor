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
import socket

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

from json_msgs.messages.sensors.drive_mngr import DriveMngrMsg
from json_msgs.messages.sensors.hpi_data import HPIDataMsg


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

        # Find a meaningful hostname to be used        
        if socket.gethostname().find('.') >= 0:
            self._host_id = socket.gethostname()
        else:
            self._host_id = socket.gethostbyaddr(socket.gethostname())[0]

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
            sensor_response_type = jsonMsg.get("sensor_response_type")
            self._log_debug("_processMsg, sensor_response_type: %s" % sensor_response_type)

            # Handle drivemanager events
            if sensor_response_type == "disk_status_drivemanager":
                # Convert event path to Drive object to handle parsing and json conversion, etc
                drive = Drive(self._host_id,
                              jsonMsg.get("event_path"),
                              jsonMsg.get("status"))

                # Check to see if the drive path is valid
                valid = drive.parse_drive_mngr_path()

                self._log_debug("_process_msg enclosureSN: %s" % drive.get_drive_enclosure() \
                                + ", diskNum: %s" % drive.get_drive_num() \
                                + ", filename: %s"  % drive.get_drive_filename() \
                                + ", diskStatus: %s"  % drive.get_drive_status())

                if not valid:
                    logger.error("_process_msg, valid: False (ignoring)")
                    return

                # Obtain json message containing all relevant data
                internal_json_msg = drive.toDriveMngrJsonMsg().getJson()

                # Send the json message to the RabbitMQ processor to transmit out
                self._log_debug("_process_msg, internal_json_msg: %s" % internal_json_msg)
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

            # Handle HPI events
            elif sensor_response_type == "disk_status_hpi":
                # Convert to Drive object to handle parsing and json conversion, etc
                drive = Drive(self._host_id,
                              jsonMsg.get("event_path"),
                              jsonMsg.get("status"),
                              jsonMsg.get("drawer"),
                              jsonMsg.get("location"),
                              jsonMsg.get("manufacturer"),
                              jsonMsg.get("productName"),
                              jsonMsg.get("productVersion"),
                              jsonMsg.get("serialNumber"),
                              jsonMsg.get("wwn"))

                # Check to see if the drive path is valid
                valid = drive.parse_hpi_path()

                self._log_debug("_process_msg enclosureSN: %s" % drive.get_drive_enclosure() \
                                + ", diskNum: %s" % drive.get_drive_num() \
                                + ", filename: %s"  % drive.get_drive_filename())

                if not valid:
                    logger.error("_process_msg, valid: False (ignoring)")
                    return
     
                # Obtain json message containing all relevant data
                internal_json_msg = drive.toHPIjsonMsg().getJson()
     
                # Send the json message to the RabbitMQ processor to transmit out
                self._log_debug("_process_msg, internal_json_msg: %s" % internal_json_msg)
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)


            # ... handle other sensor response types
            else:
                logger.warn("DiskMsgHandler, received unknown msg: %s" % jsonMsg)

        # ... handle other disk message types
        else:
            logger.warn("DiskMsgHandler, received unknown msg: %s" % jsonMsg)
        

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DiskMsgHandler, self).shutdown()


class Drive(object):
    """Object representation of a drive"""

    def __init__(self, hostId, path,
                 status         = "N/A",
                 drawer         = "N/A",
                 location       = "N/A",
                 manufacturer   = "N/A",
                 productName    = "N/A",
                 productVersion = "N/A",
                 serialNumber   = "N/A",
                 wwn            = "N/A"
                 ):
        super(Drive, self).__init__()

        self._hostId         = hostId
        self._path           = path
        self._status         = status
        self._drawer         = drawer
        self._location       = location
        self._manufacturer   = manufacturer
        self._productName    = productName
        self._productVersion = productVersion
        self._serialNumber   = serialNumber
        self._wwn            = wwn 
        self._enclosure      = "N/A"
        self._drive_num      = "N/A"        
        self._filename       = "N/A"

    def parse_drive_mngr_path(self):
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

    def parse_hpi_path(self):
        """Parse the path of the file, return True if valid file name exists in path"""
        try:
            # Parse out enclosure and drive number
            path_values = self._path.split("/")

            # See if there is a valid filename at the end: serial_number, slot, status
            # Normal path will be: [enclosure sn]/disk/[drive number]
            if len(path_values) < 3:
                return False

            # Parse out values for drive
            self._enclosure = path_values[0]
            self._drive_num = path_values[2]

            return True

        except Exception as ex:
            logger.exception("Drive, _parse_path: %s, ignoring event." % ex)
        return False

    def toDriveMngrJsonMsg(self):
        """Returns the JSON representation of a drive"""
        # Create a drive manager json object which can be
        #  be queued up for aggregation at a later time if needed
        jsonMsg = DriveMngrMsg(self._enclosure,
                               self._drive_num,
                               self._status)
        return jsonMsg

    def toHPIjsonMsg(self):
        """Returns the JSON representation of a drive"""
        # Create an HPI data json object which can be
        #  be queued up for aggregation at a later time if needed
        jsonMsg = HPIDataMsg(self._hostId,
                             self._path,
                             self._drawer,
                             self._location,
                             self._manufacturer,
                             self._productName,
                             self._productVersion,
                             self._serialNumber,
                             self._wwn)
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
    
    def get_drive_enclosure(self):
        """Return the enclosure of the drive"""
        return self._enclosure

    def get_drive_num(self):
        """Return the enclosure of the drive"""
        return self._drive_num

    def get_drive_filename(self):
        """Return the filename of the drive"""
        return self._filename

    def getHostId(self):
        return self._hostId

    def getDeviceId(self):
        return self._deviceId

    def getDrawer(self):
        return self._drawer

    def getLocation(self):
        return self._location

    def getManufacturer(self):
        return self._manufacturer

    def getProductName(self):
        return self._productName

    def getProductVersion(self):
        return self._productVersion

    def getSerialNumber(self):
        return self._serialNumber

    def getWWN(self):
        return self._wwn
