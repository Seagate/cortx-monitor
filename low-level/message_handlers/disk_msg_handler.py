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

import os
import json
import time
import syslog
import socket

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

from json_msgs.messages.sensors.drive_mngr import DriveMngrMsg
from json_msgs.messages.sensors.hpi_data import HPIDataMsg

from json_msgs.messages.actuators.ack_response import AckResponseMsg

# Modules that receive messages from this module
from message_handlers.logging_msg_handler import LoggingMsgHandler
from message_handlers.service_msg_handler import ServiceMsgHandler


class DiskMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for Disk Sensor Messages"""

    MODULE_NAME = "DiskMsgHandler"
    PRIORITY    = 2

    # Section and keys in configuration file
    DISKMSGHANDLER = MODULE_NAME.upper()
    DMREPORT_FILE  = 'dmreport_file'
    ALWAYS_LOG_IEM = 'always_log_iem'

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

        # Read in the location to serialize drive_manager.json
        self._dmreport_file = self._getDMreport_File()

        # Bool flag signifying to always log disk status even when it hasn't changed
        self._always_log_IEM = self._getAlways_log_IEM()

        # Dict of drive manager data for drives
        self._drvmngr_drives = {}

        # Dict of HPI data for drives
        self._hpi_drives = {}

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

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception("DiskMsgHandler restarting: %s" % ae)

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger"""
        self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

        if isinstance(jsonMsg, dict) == False:
            jsonMsg = json.loads(jsonMsg)

        # Handle sensor response type messages that update the drive's state
        if jsonMsg.get("sensor_response_type") is not None:
            sensor_response_type = jsonMsg.get("sensor_response_type")
            self._log_debug("_processMsg, sensor_response_type: %s" % sensor_response_type)

            # Serial number is used as an index into dicts
            serial_number = jsonMsg.get("serial_number")

            # Drivemanager events from systemd watchdog sensor
            if sensor_response_type == "disk_status_drivemanager":

                # An * in the serial_number field indicates a request to send all the current data
                if serial_number == "*":
                    self._transmit_all_drivemanager_responses()
                else:
                    self._process_drivemanager_response(jsonMsg, serial_number)

            # Halon Disk Status (HDS log) events from the logging msg handler
            elif sensor_response_type == "disk_status_HDS":
                self._process_HDS_response(jsonMsg, serial_number)

            # HPI events from the HPI monitor sensor
            elif sensor_response_type == "disk_status_hpi":
                # An * in the serial_number field indicates a request to send all the current data
                if serial_number == "*":
                    self._transmit_all_HPI_responses()
                else:
                    self._process_hpi_response(jsonMsg, serial_number)

            # ... handle other disk sensor response types
            else:
                logger.warn("DiskMsgHandler, received unknown sensor response msg: %s" % jsonMsg)

        # Handle sensor request type messages
        # TODO: Break this apart into small methods on a rainy day
        elif jsonMsg.get("sensor_request_type") is not None:
            sensor_request_type = jsonMsg.get("sensor_request_type")
            self._log_debug("_processMsg, sensor_request_type: %s" % sensor_request_type)

            # Serial number is used as an index into dicts
            serial_number = jsonMsg.get("serial_number")
            self._log_debug("_processMsg, serial_number: %s" % serial_number)

            node_request = jsonMsg.get("node_request")

            # Parse out the UUID and save to send back in response if it's available
            uuid = None
            if jsonMsg.get("uuid") is not None:
                uuid = jsonMsg.get("uuid")
            self._log_debug("_processMsg, sensor_request_type: %s, uuid: %s" % (sensor_request_type, uuid))

            if sensor_request_type == "disk_smart_test":
                # If the serial number is an asterisk then send over all the smart results for all drives
                if serial_number == "*":
                    for serial_number in self._drvmngr_drives:
                        drive = self._drvmngr_drives[serial_number]

                        if drive.get_drive_status().lower() == "inuse_ok" or \
                           drive.get_drive_status().lower() == "ok_none":
                            response = "Passed"
                        else:
                            response = "Failed"

                        self._log_debug("_processMsg, disk smart test, drive test status: %s" % 
                                    response)

                        request = "SMART_TEST: serial number: {}, IP: {}" \
                                    .format(drive.getSerialNumber(), node_request)

                        json_msg = AckResponseMsg(request, response, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                    return

                elif self._drvmngr_drives.get(serial_number) is not None:
                    if self._drvmngr_drives[serial_number].get_drive_status().lower() == "inuse_ok" or \
                       self._drvmngr_drives[serial_number].get_drive_status().lower() == "ok_none":
                        response = "Passed"
                    else:
                        response = "Failed"
                    self._log_debug("_processMsg, disk smart test, drive test status: %s" % 
                                    response)
                else:
                    self._log_debug("_processMsg, disk smart test data not yet available")
                    response = "Error: SMART results not yet available for drive, please try again later."

                json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif sensor_request_type == "drvmngr_status":
                # If the serial number is an asterisk then send over all the drivemanager results for all drives
                if serial_number == "*":
                    for serial_number in self._drvmngr_drives:
                        drive = self._drvmngr_drives[serial_number]

                        # Obtain json message containing all relevant data
                        internal_json_msg = drive.toDriveMngrJsonMsg(uuid=uuid).getJson()

                        # Send the json message to the RabbitMQ processor to transmit out
                        self._log_debug("_process_msg, internal_json_msg: %s" % internal_json_msg)
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

                    # Send over a msg on the ACK channel notifying success
                    response = "All Drive manager data sent successfully"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                elif self._drvmngr_drives.get(serial_number) is not None:
                    drive = self._drvmngr_drives[serial_number]
                    # Obtain json message containing all relevant data
                    internal_json_msg = drive.toDriveMngrJsonMsg(uuid=uuid).getJson()

                    # Send the json message to the RabbitMQ processor to transmit out
                    self._log_debug("_process_msg, internal_json_msg: %s" % internal_json_msg)
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

                    # Send over a msg on the ACK channel notifying success
                    response = "Drive manager data sent successfully"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                else:
                    # Send over a msg on the ACK channel notifying failure
                    response = "Drive not found in drive manager data"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif sensor_request_type == "hpi_status":
                # If the serial number is an asterisk then send over all the hpi results for all drives
                if serial_number == "*":
                    for serial_number in self._hpi_drives:
                        drive = self._hpi_drives[serial_number]

                        # Obtain json message containing all relevant data
                        internal_json_msg = drive.toHPIjsonMsg(uuid=uuid).getJson()

                        # Send the json message to the RabbitMQ processor to transmit out
                        self._log_debug("_process_msg, internal_json_msg: %s" % internal_json_msg)
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

                    # Send over a msg on the ACK channel notifying success
                    response = "All HPI data sent successfully"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                elif self._hpi_drives.get(serial_number) is not None:
                    drive = self._hpi_drives[serial_number]
                    # Obtain json message containing all relevant data
                    internal_json_msg = drive.toHPIjsonMsg(uuid=uuid).getJson()

                    # Send the json message to the RabbitMQ processor to transmit out
                    self._log_debug("_process_msg, internal_json_msg: %s" % internal_json_msg)
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

                    # Send over a msg on the ACK channel notifying success
                    response = "Drive manager data sent successfully"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                else:
                    # Send over a msg on the ACK channel notifying failure
                    response = "Drive not found in HPI data"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            # ... handle other disk sensor request types
            else:
                logger.warn("DiskMsgHandler, received unknown sensor request msg: %s" % jsonMsg)

        else:
            logger.warn("DiskMsgHandler, received unknown msg: %s" % jsonMsg)

            # Send over a msg on the ACK channel notifying failure
            response = "DiskMsgHandler, received unknown msg: %s" % jsonMsg
            json_msg = AckResponseMsg(node_request, response, uuid).getJson()
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def _process_HDS_response(self, jsonMsg, serial_number):
        """Process a disk_status_HDS msg sent from logging msg handler"""

        # See if we have an existing drive object in dict and update it
        if self._drvmngr_drives.get(serial_number) is not None:
            status = jsonMsg.get("status")
            reason = jsonMsg.get("reason")

            # Update the drive with the new status and reason
            drive = self._drvmngr_drives.get(serial_number)
            status_reason = "{}_{}".format(status, reason)
            drive.set_drive_status(status_reason)

            # Serialize to DCS directory for RAS
            self._serialize_disk_status()

        # Allow HDS msg to create a fake drive object for testing via CLI
        else:
            event_path = "HPI_Data_Not_Available/disk/-1/status"

            drive = Drive(self._host_id,
                          event_path,
                          jsonMsg.get("status"),
                          serial_number,
                          path_id="fictional/drive/path_id/for/testing")

            # Parse the fictional event path so enclosure S/N & disk number is populated
            drive.parse_drive_mngr_path()

        # Obtain json message containing all relevant data
        internal_json_msg = drive.toDriveMngrJsonMsg().getJson()

        # Send the json message to the RabbitMQ processor to transmit out
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

    def _transmit_all_drivemanager_responses(self):
        """Transmit all drivemanager data for every drive"""
        for drive in self._drvmngr_drives:
            # Obtain json message containing all relevant data
            internal_json_msg = drive.toDriveMngrJsonMsg().getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

    def _transmit_all_HPI_responses(self):
        """Transmit all HPI data for every drive"""
        for drive in self.self._hpi_drives:
            # Obtain json message containing all relevant data
            internal_json_msg = drive.toHPIjsonMsg().getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

    def _process_drivemanager_response(self, jsonMsg, serial_number):
        """Process a disk_status_drivemanager msg sent from systemd watchdog"""

        # See if we have an existing drive object and update it
        if self._drvmngr_drives.get(serial_number) is not None:
            status  = jsonMsg.get("status")
            path_id = jsonMsg.get("path_id")

            # Do nothing if the status and path_id didn't change
            drive = self._drvmngr_drives.get(serial_number)
            if drive.get_drive_status().lower() == status.lower() and \
                drive.get_path_id() == path_id:

                if not self._always_log_IEM:
                    return

            # Ignore if current drive status has 'halon' in it which has precedence over all others
            if "halon" in drive.get_drive_status().lower():
                logger.info("DiskMsgHandler, _process_drivemanager_response, drive status is " \
                            "currently set from Halon which has precedence so ignoring.")
                return

            # Update the status and path_id
            drive.set_drive_status(status)
            drive.set_path_id(path_id)

            # Log an IEM
            self._log_IEM(drive)

        # Create a new Drive object and add it to dict
        else:
            # Initialize event path with a NotAvailable enclosure s/n and disk #
            event_path = "HPI_Data_Not_Available/disk/-1/status"
            # Retrieve hpi drive object
            try:
                hpi_drive = self._hpi_drives[serial_number]
                # Build event path used in json msg
                event_path = hpi_drive.get_drive_enclosure() + "/disk/" + \
                             hpi_drive.get_drive_num() + "/status"
            except Exception as ae:
                logger.info("DiskMsgHandler, No HPI data for serial number: %s" % serial_number)

            drive = Drive(self._host_id,
                          event_path,
                          jsonMsg.get("status"),
                          serial_number,
                          path_id=jsonMsg.get("path_id"))

            # Check to see if the event path is valid and parse out enclosure s/n and disk num
            valid = drive.parse_drive_mngr_path()
            if not valid:
                logger.error("DiskMsgHandler, event_path valid: False (ignoring)")
                return

            # Update the dict of drive manager drives and write s/n and status to file
            self._drvmngr_drives[serial_number] = drive

            # Log an IEM if flag is set to do so
            if self._always_log_IEM:
                self._log_IEM(drive)

        # Obtain json message containing all relevant data
        internal_json_msg = drive.toDriveMngrJsonMsg().getJson()

        # Send the json message to the RabbitMQ processor to transmit out
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        # Write the serial number and status to DCS file
        self._serialize_disk_status()

    def _process_hpi_response(self, jsonMsg, serial_number):
        """Process a hpi_status msg sent from HPI Monitor Sensor"""

        # Convert to Drive object to handle parsing and json conversion, etc
        drive = Drive(self._host_id,
                      jsonMsg.get("event_path"),
                      jsonMsg.get("status"),
                      serial_number,
                      jsonMsg.get("drawer"),
                      jsonMsg.get("location"),
                      jsonMsg.get("manufacturer"),
                      jsonMsg.get("productName"),
                      jsonMsg.get("productVersion"),
                      jsonMsg.get("wwn"))

        # Check to see if the drive path is valid
        valid = drive.parse_hpi_path()

        if not valid:
            logger.error("DiskMsgHandler, valid: False (ignoring)")
            return

        # Update the dict of hpi drives
        self._hpi_drives[serial_number] = drive

        # Obtain json message containing all relevant data
        internal_json_msg = drive.toHPIjsonMsg().getJson()

        # Send the json message to the RabbitMQ processor to transmit out
        self._log_debug("_process_msg, internal_json_msg: %s" % internal_json_msg)
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        # See if there is a drivemanager drive available and update its HPI data if changed
        if self._drvmngr_drives.get(serial_number) is not None:

            # Ignore if nothing changed otherwise send json msg, serialize and log IEM
            drivemngr_drive = self._drvmngr_drives.get(serial_number)
            if drivemngr_drive.get_drive_enclosure() == drive.get_drive_enclosure() and \
                drivemngr_drive.get_drive_num() == drive.get_drive_num():
                    return

            drivemngr_drive.set_drive_enclosure(drive.get_drive_enclosure())
            drivemngr_drive.set_drive_num(drive.get_drive_num())

            # Obtain json message containing all relevant data
            internal_json_msg = drivemngr_drive.toDriveMngrJsonMsg().getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

            # Write the serial number and status to DCS file
            self._serialize_disk_status()

            # Log an IEM because we have new data
            self._log_IEM(drivemngr_drive)

    def _serialize_disk_status(self):
        """Writes the current disks in {serial:status} format"""
        try:
            dmreport_dir = os.path.dirname(self._dmreport_file)
            if not os.path.exists(dmreport_dir):
                os.makedirs(dmreport_dir)

            drives_list = []
            json_dict = {}
            for serial_num, drive in self._drvmngr_drives.iteritems():
                # Don't serialize drives that have no HPI data
                if drive.get_drive_enclosure() == "HPI_Data_Not_Available":
                    continue

                # Split apart the drive status into status and reason values
                # Status is first word before the first '_'
                status, reason = str(drive.get_drive_status()).split("_", 1)
                drives = {}
                drives["serial_number"] = drive.getSerialNumber()
                drives["status"] = status
                drives["reason"] = reason
                drives_list.append(drives)

            json_dict["last_update_time"] = time.strftime("%c")
            json_dict["drives"] = drives_list
            json_dump = json.dumps(json_dict, sort_keys=True)
            with open(self._dmreport_file, "w+") as dm_file:                
                dm_file.write(json_dump)
        except Exception as ae:
            logger.exception(ae)

    def _log_IEM(self, drive):
        """Sends an IEM to logging msg handler"""
        # Split apart the drive status into status and reason values
        # Status is first word before the first '_'
        status, reason = str(drive.get_drive_status()).split("_", 1)
        self._log_debug("_log_IEM, status: %s reason:%s" % (status, reason))

        log_msg = ""
        if status.lower() == "empty" or \
           status.lower() == "unused":   # Backwards compatible with external drivemanager
            log_msg = "IEC: 020001002: Drive removed"

        elif status.lower() == "ok" or \
             status.lower() == "inuse":  # Backwards compatible with external drivemanager
            log_msg = "IEC: 020001001: Drive added/back to normal state"

        elif status.lower() == "failed":
            # Only handling SMART failures for now
            if "smart" in reason.lower():
                log_msg = "IEC: 020002002: SMART validation test has failed"

        if len(log_msg) == 0:
            if "halon" in status.lower():
                # These status are sent from Halon as HDS log types and get handled in logging_msg_handler
                return
            else:
                # The status was generated within sspl-ll but we don't recognize it
                logger.info("DiskMsgHandler, Unknown disk status/reason: {}/{}".format(status, reason))
                return

        json_data = {"enclosure_serial_number": drive.get_drive_enclosure(),
                         "disk_serial_number": drive.getSerialNumber(),
                         "slot": drive.get_drive_num(), 
                         "status": status,
                         "reason": reason,
                         "hostname": self._host_id,
                         "path_id": drive.get_path_id()
                         }

        self._log_debug("_log_IEM, log_msg: %{}:{}".format(log_msg, json.dumps(json_data, sort_keys=True)))
        internal_json_msg = json.dumps(
                    {"actuator_request_type" : {
                        "logging": {
                            "log_level": "LOG_WARNING",
                            "log_type": "IEM",
                            "log_msg": "{}:{}".format(log_msg, json.dumps(json_data, sort_keys=True))
                            }
                        }
                     })

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def _getDMreport_File(self):
        """Retrieves the file location"""
        return self._conf_reader._get_value_with_default(self.DISKMSGHANDLER,
                                                         self.DMREPORT_FILE,
                                                         '/tmp/dcs/dmreport/drive_manager.json')
    def _getAlways_log_IEM(self):
        """Retrieves flag signifying we should always log disk status as an IEM even if they 
            haven't changed.  This is useful for always logging SMART results"""
        val = bool(self._conf_reader._get_value_with_default(self.DISKMSGHANDLER,
                                                              self.ALWAYS_LOG_IEM,
                                                              False))
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(DiskMsgHandler, self).shutdown()


class Drive(object):
    """Object representation of a drive"""

    def __init__(self, hostId, event_path,
                 status         = "N/A",
                 serialNumber   = "N/A",
                 drawer         = "N/A",
                 location       = "N/A",
                 manufacturer   = "N/A",
                 productName    = "N/A",
                 productVersion = "N/A",
                 wwn            = "N/A",
                 path_id        = "N/A"
                 ):
        super(Drive, self).__init__()

        self._hostId         = hostId
        self._event_path     = event_path
        self._status         = status
        self._serialNumber   = serialNumber
        self._drawer         = drawer
        self._location       = location
        self._manufacturer   = manufacturer
        self._productName    = productName
        self._productVersion = productVersion
        self._wwn            = wwn
        self._path_id        = path_id
        self._enclosure      = "N/A"
        self._drive_num      = -1
        self._filename       = "N/A"

    def parse_drive_mngr_path(self):
        """Parse the path of the file, return True if valid file name exists in path"""
        try:
            # Parse out enclosure and drive number
            path_values = self._event_path.split("/")

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
            path_values = self._event_path.split("/")

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

    def toDriveMngrJsonMsg(self, uuid=None):
        """Returns the JSON representation of a drive"""
        # Create a drive manager json object which can be
        #  be queued up for aggregation at a later time if needed
        jsonMsg = DriveMngrMsg(self._enclosure,
                               self._drive_num,
                               self._status,
                               self._serialNumber,
                               self._path_id)
        if uuid is not None:
            jsonMsg.set_uuid(uuid)

        return jsonMsg

    def toHPIjsonMsg(self, uuid=None):
        """Returns the JSON representation of a drive"""
        # Create an HPI data json object which can be
        #  be queued up for aggregation at a later time if needed
        jsonMsg = HPIDataMsg(self._hostId,
                             self._event_path,
                             self._drawer,
                             self._location,
                             self._manufacturer,
                             self._productName,
                             self._productVersion,
                             self._serialNumber,
                             self._wwn,
                             self._enclosure,
                             self._drive_num)
        if uuid is not None:
            jsonMsg.set_uuid(uuid)

        return jsonMsg

    def set_path_id(self, path_id):
        """Sets a drive's path_id"""
        self._path_id = path_id

    def set_drive_status(self, status):
        """Sets a drive status"""
        self._status = status

    def set_drive_enclosure(self, enclosure):
        """Set the drive eclosure serial_number"""
        self._enclosure = enclosure

    def set_drive_num(self, drive_num):
        """Set the drive number"""
        self._drive_num = drive_num

    def get_path_id(self):
        """Return the by-id path of drive"""
        return self._path_id

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
