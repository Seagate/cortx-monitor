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
  Description:       Message Handler for Disk Sensor Messages
 ****************************************************************************
"""

import json
import os
import socket
import subprocess
import time

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.rabbitmq.rabbitmq_egress_processor import \
    RabbitMQegressProcessor
from framework.utils.conf_utils import SSPL_CONF, Conf
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.ack_response import AckResponseMsg
from json_msgs.messages.sensors.drive_mngr import DriveMngrMsg
from json_msgs.messages.sensors.expander_reset import ExpanderResetMsg
from json_msgs.messages.sensors.hpi_data import HPIDataMsg
from json_msgs.messages.sensors.node_hw_data import NodeIPMIDataMsg
# Modules that receive messages from this module
from message_handlers.logging_msg_handler import LoggingMsgHandler


class DiskMsgHandler(ScheduledModuleThread, InternalMsgQ):
    """Message Handler for Disk Sensor Messages"""

    MODULE_NAME = "DiskMsgHandler"
    PRIORITY    = 2

    # Section and keys in configuration file
    DISKMSGHANDLER    = MODULE_NAME.upper()
    DMREPORT_FILE     = 'dmreport_file'
    DISKINFO_FILE     = 'diskinfo_file'
    MAX_DM_EVENTS     = 'max_drivemanager_events'
    MAX_DM_EVENTS_INT = 'max_drivemanager_event_interval'

    ALWAYS_LOG_IEM = 'always_log_iem'

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["LoggingMsgHandler", "RabbitMQegressProcessor"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """ @return: name of the module."""
        return DiskMsgHandler.MODULE_NAME

    def __init__(self):
        super(DiskMsgHandler, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        # Flag to indicate suspension of module
        self._suspended = False

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(DiskMsgHandler, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(DiskMsgHandler, self).initialize_msgQ(msgQlist)

        # Find a meaningful hostname to be used
        self._host_id = socket.getfqdn()
        # getfqdn() function checks the socket.gethostname() to get the host name if it not available
        # then it try to find host name from socket.gethostbyaddr(socket.gethostname())[0] and return the
        # meaningful host name priviously we chking the this two conditions explicitly which is implicitly
        # doing by getfqdn() function. so removing the code and adding the getfqdn() function to get Hostname.
        # Read in the location to serialize drive_manager.json
        self._dmreport_file = self._getDMreport_File()

        # Read in the location to serialize disk_info.json
        self._disk_info_file = self._getDiskInfo_File()

        # Bool flag signifying to always log disk status even when it hasn't changed
        self._always_log_IEM = self._getAlways_log_IEM()

        # Dict of drive manager data for drives
        self._drvmngr_drives = {}

        # Dict of HPI data for drives
        self._hpi_drives = {}

        # Current /dev/sgX which changes during expander resets
        self._scsi_generic = "N/A"

        # Counter to track drives with drivemanager events for determining partial expander resets
        self._drivemanager_events_counter = 0

        # Time of first drivemanager event in an incoming set for determining partial expander resets
        self._first_drivemanager_event_tm = 0

        # Get values for max number of events in the seconds interval to flag a partial expander reset
        self._getDM_exp_reset_values()

        # Initialize _scsi_generic to the current /dev/sgX value
        # DEPRECATED for drivemanager interval checks
        #self._check_expander_reset()

        # Dump startup info to journal for debugging
        logger.info(f"Current /dev/sg device: {self._scsi_generic}")

    def run(self):
        """Run the module periodically on its own thread."""

        #self._set_debug(True)
        #self._set_debug_persist(True)

        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(1, self._priority, self.run, ())
            return

        self._log_debug("Start accepting requests")

        try:
            # Block on message queue until it contains an entry
            jsonMsg, _ = self._read_my_msgQ()
            if jsonMsg is not None:
                self._process_msg(jsonMsg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                jsonMsg, _ = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._process_msg(jsonMsg)

        except Exception as ae:
            # Log it and restart the whole process when a failure occurs
            logger.exception(f"DiskMsgHandler restarting: {ae}")

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and hands off to the appropriate logger"""
        self._log_debug(f"_process_msg, jsonMsg: {jsonMsg}")

        if isinstance(jsonMsg, dict) is False:
            jsonMsg = json.loads(jsonMsg)

        # Handle sensor response type messages that update the drive's state
        if jsonMsg.get("sensor_response_type") is not None:
            sensor_response_type = jsonMsg.get("sensor_response_type")
            self._log_debug(f"_processMsg, sensor_response_type: {sensor_response_type}")

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
                    # Check for a valid WWN & serial number
                    wwn = jsonMsg.get("wwn")
                    if serial_number == "ZBX_NOTPRESENT" or \
                       wwn == "ZBX_NOTPRESENT":
                        self._process_hpi_response_ZBX_NOTPRESENT(jsonMsg)
                    else:
                        self._process_hpi_response(jsonMsg, serial_number)

            elif sensor_response_type == "node_disk":
                node_disk_msg = NodeIPMIDataMsg(jsonMsg.get("response"))
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), node_disk_msg.getJson())
            # ... handle other disk sensor response types
            else:
                logger.warn(f"DiskMsgHandler, received unknown sensor response msg: {jsonMsg}")

        # Handle sensor request type messages
        # TODO: Break this apart into small methods on a rainy day
        elif jsonMsg.get("sensor_request_type") is not None:
            sensor_request_type = jsonMsg.get("sensor_request_type")
            self._log_debug(f"_processMsg, sensor_request_type: {sensor_request_type}")

            # Serial number is used as an index into dicts
            serial_number = jsonMsg.get("serial_number")
            self._log_debug(f"_processMsg, serial_number: {serial_number}")

            node_request = jsonMsg.get("node_request")

            # Parse out the UUID and save to send back in response if it's available
            uuid = None
            if jsonMsg.get("uuid") is not None:
                uuid = jsonMsg.get("uuid")
            self._log_debug(f"_processMsg, sensor_request_type: {sensor_request_type}, uuid: {uuid}")

            if sensor_request_type == "disk_smart_test":
                # This is currently deprecated and unused as requests for SMART tests now actually run
                #  a new test instead of just returning the results from the last test.  The
                #  NodeControllerMsgHandler now relays requests to the DiskMonitor to run the test

                # If the serial number is an asterisk then send over all the smart results for all drives
                if serial_number == "*":
                    for serial_number in self._drvmngr_drives:
                        drive = self._drvmngr_drives[serial_number]

                        if "failed_smart" in drive.get_drive_status().lower():
                            response = "Failed"
                        else:
                            response = "Passed"

                        self._log_debug(f"_processMsg, disk smart test, drive test status: {response}")

                        request = f"SMART_TEST: {drive.getSerialNumber()}"

                        json_msg = AckResponseMsg(request, response, uuid).getJson()
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                    return

                elif self._drvmngr_drives.get(serial_number) is not None:
                    if "failed_smart" in self._drvmngr_drives[serial_number].get_drive_status().lower():
                        response = "Failed"
                    else:
                        response = "Passed"

                    self._log_debug(f"_processMsg, disk smart test, drive test status: {response}")
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
                        self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

                    # Send over a msg on the ACK channel notifying success
                    response = "All Drive manager data sent successfully"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                elif serial_number == "serialize":
                    # Create disk_info.json
                    self._serialize_disk_info()

                elif self._drvmngr_drives.get(serial_number) is not None:
                    drive = self._drvmngr_drives[serial_number]
                    # Obtain json message containing all relevant data
                    internal_json_msg = drive.toDriveMngrJsonMsg(uuid=uuid).getJson()

                    # Send the json message to the RabbitMQ processor to transmit out
                    self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
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
                        self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
                        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

                    # Send over a msg on the ACK channel notifying success
                    response = "All HPI data sent successfully"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                elif serial_number == "serialize":
                    # Create disk_info.json
                    self._serialize_disk_info()

                elif self._hpi_drives.get(serial_number) is not None:
                    drive = self._hpi_drives[serial_number]
                    # Obtain json message containing all relevant data
                    internal_json_msg = drive.toHPIjsonMsg(uuid=uuid).getJson()

                    # Send the json message to the RabbitMQ processor to transmit out
                    self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

                    # Send over a msg on the ACK channel notifying success
                    response = "HPI data sent successfully"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

                else:
                    # Send over a msg on the ACK channel notifying failure
                    response = "Drive not found in HPI data"
                    json_msg = AckResponseMsg(node_request, response, uuid).getJson()
                    self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

            elif sensor_request_type == "sim_event":
                logger.info(f"DiskMsgHandler, node_request: {node_request} serial_number: {serial_number}" )

                if node_request == "DRIVE_UNINSTALL":
                    logger.info("DiskMsgHandler, simulating drive uninstall")
                    self._sim_drive_uninstall(serial_number)

                elif node_request == "DRIVE_INSTALL":
                    logger.info("DiskMsgHandler, simulating drive install")
                    self._sim_drive_install(serial_number)

                elif node_request == "EXP_RESET":
                    logger.info("DiskMsgHandler, simulating exp_reset")
                    self._sim_exp_reset(serial_number)

            # ... handle other disk sensor request types
            else:
                logger.warn(f"DiskMsgHandler, received unknown sensor request msg: {jsonMsg}")

        else:
            logger.warn(f"DiskMsgHandler, received unknown msg: {jsonMsg}")

            # Send over a msg on the ACK channel notifying failure
            response = f"DiskMsgHandler, received unknown msg: {jsonMsg}"
            json_msg = AckResponseMsg(node_request, response, uuid).getJson()
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), json_msg)

    def _sim_exp_reset(self, serial_number):
        """Handle simulating an expander reset"""
        # Send the expander reset message
        expanderResetMsg = ExpanderResetMsg()
        internal_json_msg = expanderResetMsg.getJson()

        # Send the json message to the RabbitMQ processor to transmit out
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        # Loop thru all the drivemanager drives and set to EMPTY_None to simulate drive dropping out of OS
        for serial_number in self._drvmngr_drives:
            drive = self._drvmngr_drives[serial_number]

            # Obtain json message containing all relevant data
            json_msg = drive.toDriveMngrJsonMsg()
            json_msg.setStatus("EMPTY_None")
            internal_json_msg = json_msg.getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        # Loop thru all the drivemanager drives and set to EMPTY_None to simulate drive dropping out of OS
        for serial_number in self._drvmngr_drives:
            drive = self._drvmngr_drives[serial_number]

            # Obtain json message containing all relevant data
            json_msg = drive.toDriveMngrJsonMsg()
            json_msg.setStatus("OK_None")
            internal_json_msg = json_msg.getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

    def _sim_drive_uninstall(self, serial_number):
        """Handle simulate drive uninstalled events sent from cli"""
        if self._drvmngr_drives.get(serial_number) is not None:
            drive = self._drvmngr_drives[serial_number]

            # Obtain json message containing all relevant data
            json_msg = drive.toDriveMngrJsonMsg()
            json_msg.setStatus("EMPTY_None")
            internal_json_msg = json_msg.getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        if self._hpi_drives.get(serial_number) is not None:
            drive = self._hpi_drives[serial_number]

            # Obtain json message containing all relevant data
            json_msg = drive.toHPIjsonMsg()
            json_msg.setDiskPowered(False)
            json_msg.setDiskInstalled(False)
            internal_json_msg = json_msg.getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

    def _sim_drive_install(self, serial_number):
        """Handle simulate drive installed events sent from cli"""
        if self._drvmngr_drives.get(serial_number) is not None:
            drive = self._drvmngr_drives[serial_number]

            # Obtain json message containing all relevant data
            json_msg = drive.toDriveMngrJsonMsg()
            json_msg.setStatus("OK_None")
            internal_json_msg = json_msg.getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        if self._hpi_drives.get(serial_number) is not None:
            drive = self._hpi_drives[serial_number]

            # Obtain json message containing all relevant data
            json_msg = drive.toHPIjsonMsg()
            json_msg.setDiskPowered(True)
            json_msg.setDiskInstalled(True)
            internal_json_msg = json_msg.getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)


    def _process_HDS_response(self, jsonMsg, serial_number):
        """Process a disk_status_HDS msg sent from logging msg handler"""

        # See if we have an existing drive object in dict and update it
        if self._drvmngr_drives.get(serial_number) is not None:
            status = jsonMsg.get("status")
            reason = jsonMsg.get("reason")

            # Update the drive with the new status and reason
            drive = self._drvmngr_drives.get(serial_number)
            status_reason = f"{status}_{reason}"
            drive.set_drive_status(status_reason)

            # Serialize to DCS directory for RAS
            self._serialize_disk_status()

        # Halon sent a HDS log message but we don't know about the drive, error
        else:
            logger.warn(f"DiskMsgHandler, _process_HDS_response, received HDS request \
                        for unknown drive: {serial_number}, jsonMsg: {str(jsonMsg)}" )

    def _transmit_all_drivemanager_responses(self):
        """Transmit all drivemanager data for every drive"""
        for drive in self._drvmngr_drives:
            # Obtain json message containing all relevant data
            internal_json_msg = drive.toDriveMngrJsonMsg().getJson()

            # Send the json message to the RabbitMQ processor to transmit out
            self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

    def _transmit_all_HPI_responses(self):
        """Transmit all HPI data for every drive"""
        for drive in self._hpi_drives:
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

            # Check for expander reset by examining scsi generic value changing
            # DEPRECATED for drivemanager interval checks
            # self._check_expander_reset()

            # Check for expander reset by examining number of EMPTY_None drivemanager events within an interval
            if status == "EMPTY_None":
                self._check_drivemanager_events_interval()

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
            event_path     = "HPI_Data_Not_Available/disk/-1/status"
            # Retrieve hpi drive object
            try:
                hpi_drive = self._hpi_drives[serial_number]
                # Build event path used in json msg
                event_path = f"{hpi_drive.get_drive_enclosure()}/disk/    \
                             {hpi_drive.get_drive_num()}/status"
            except Exception as ae:
                logger.info(f"DiskMsgHandler, No HPI data for serial number: {serial_number}")

            drive = Drive(self._host_id,
                          event_path,
                          jsonMsg.get("status"),
                          serial_number,
                          path_id=jsonMsg.get("path_id"),
                          device_name=jsonMsg.get("device_name"))

            # Check to see if the event path is valid and parse out enclosure s/n and disk num
            valid = drive.parse_drive_mngr_path()
            if not valid:
                logger.error("DiskMsgHandler, event_path valid: False (ignoring)")
                # TODO - For simulate command, path may not be valid. Check on HW
                # return

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
                      jsonMsg.get("wwn"),
                      jsonMsg.get("disk_installed"),
                      jsonMsg.get("disk_powered"))

        # Check to see if the drive path is valid
        valid = drive.parse_hpi_path()

        if not valid:
            logger.error("DiskMsgHandler, valid: False (ignoring)")
            return

        # If it's an installed and powered HPI event then see if there was already a drive in this location and delete it
        if jsonMsg.get("disk_installed") == True and \
           jsonMsg.get("disk_powered") == True:
            self._remove_replaced_drive(serial_number, drive.get_drive_enclosure(), drive.get_drive_num())

        # Update the dict of hpi drives
        self._hpi_drives[serial_number] = drive

        # Obtain json message containing all relevant data
        internal_json_msg = drive.toHPIjsonMsg().getJson()

        # Send the json message to the RabbitMQ processor to transmit out
        self._log_debug(f"_process_msg, internal_json_msg: {internal_json_msg}")
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        # See if there is a drivemanager drive available and update its HPI data if changed
        if self._drvmngr_drives.get(serial_number) is not None:
            # Ignore if nothing changed otherwise send json msg, serialize and log IEM
            drivemngr_drive = self._drvmngr_drives.get(serial_number)
            if drivemngr_drive.get_drive_enclosure() != drive.get_drive_enclosure() or \
                drivemngr_drive.get_drive_num() != drive.get_drive_num():

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

        # Have the drivemanager resend the drive's state in the OS
        if self._drvmngr_drives:
            internal_json_msg = json.dumps(
                {"sensor_request_type" : "resend_drive_status",
                    "serial_number" : serial_number
                })
            self._write_internal_msgQ("DiskMonitor", internal_json_msg)

    def _remove_replaced_drive(self, serial_number, enclosure, drive_num):
        """Check for a drive being replaced with a new one and delete the old one"""
        # Loop thru the dict of drivemanager objects and see if there is a drive at this location in the drawer
        for old_serial_num, drive in list(self._drvmngr_drives.items()):
            try:
                if enclosure == drive.get_drive_enclosure() and \
                   drive_num == drive.get_drive_num() and \
                   serial_number != old_serial_num:

                    logger.info(f"DiskMsgHandler, _remove_replaced_drive, found previous drive       \
                                                                at num: {drive_num}, sn: {old_serial_num}" )

                    # Found a previous drive in this location so delete it
                    self._drvmngr_drives[old_serial_num] = None
                    self._hpi_drives[old_serial_num]     = None

            except Exception as ae:
                logger.warn(f"DiskMsgHandler, _remove_replaced_drive exception: {str(ae)}")
                logger.info(f"new sn: {serial_number}, old sn: {old_serial_num}, drive num: {drive_num}, encl sn: {enclosure}" )

    def _process_hpi_response_ZBX_NOTPRESENT(self, jsonMsg):
        """Handle HPI data with serial number or wwn = ZBX_NOTPRESENT"""

        # If the serial number is set to the default then write it out as not present for RAS and restart openhpid
        if jsonMsg.get("serial_number") == "ZBX_NOTPRESENT":
            # Disk is not available in HPI, started up with a drive missing or HPI needs refreshed
            logger.info(f"DiskMsgHandler, S/N=ZBX_NOTPRESENT for {jsonMsg.get('event_path')}")

            # Manually populate the /tmp/dcs/dmreport/'event_path' files
            dmreport_dir = os.path.dirname("/tmp/dcs/dmreport")
            disk_dir = f"{dmreport_dir}/{jsonMsg.get('event_path')}"
            if not os.path.exists(disk_dir):
                os.makedirs(disk_dir)

            self._write_file(f"{disk_dir}/drawer", jsonMsg.get("drawer"))
            self._write_file(f"{disk_dir}/location", jsonMsg.get("location"))

            if not os.path.exists(f"{disk_dir}/serial_number"):
                self._write_file(f"{disk_dir}/serial_number", "NOTPRESENT")

            self._write_file(f"{disk_dir}/status", "EMPTY")
            self._write_file(f"{disk_dir}/reason", "None")

        else:
            # See if there is a HPI drive available based upon event path on fs
            drive = None
            event_path = jsonMsg.get("event_path")

            for serial_number in self._hpi_drives:
                hpi_drive = self._hpi_drives[serial_number]
                if hpi_drive.get_event_path() == event_path:
                    drive = hpi_drive
                    break

            if drive is not None:
                logger.info(f"DiskMsgHandler, S/N=ZBX_NOTPRESENT, HPI data found for {jsonMsg.get('event_path')}")

                # Don't step on valid values with ZBX_NOTPRESENT
                wwn = jsonMsg.get("wwn")
                if wwn == "ZBX_NOTPRESENT":
                    wwn = drive.getWWN()

                productName = jsonMsg.get("productName")
                if productName == "ZBX_NOTPRESENT":
                    productName = drive.getProductName()

                productVersion = jsonMsg.get("productVersion")
                if productVersion == "ZBX_NOTPRESENT":
                    productVersion = drive.getProductVersion()

                manufacturer = jsonMsg.get("manufacturer")
                if manufacturer == "ZBX_NOTPRESENT":
                    manufacturer = drive.getManufacturer()

                # Update the fields except for serial number and send json msg
                serial_number = drive.getSerialNumber()
                drive = Drive(self._host_id,
                          jsonMsg.get("event_path"),
                          jsonMsg.get("status"),
                          jsonMsg.get("serial_number"),
                          jsonMsg.get("drawer"),
                          jsonMsg.get("location"),
                          manufacturer,
                          productName,
                          productVersion,
                          wwn,
                          jsonMsg.get("disk_installed"),
                          jsonMsg.get("disk_powered"))

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
                self._log_debug(f"_process_hpi_response_ZBX_NOTPRESENT, internal_json_msg: {internal_json_msg}")
                self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

    def _write_file(self, file_path, contents):
        """Writes the contents to file_path"""
        with open(file_path, "w+") as disk_file:
            disk_file.write(contents + "\n")

    def _serialize_disk_status(self):
        """Writes the current disks in {serial:status} format"""
        try:
            dmreport_dir = os.path.dirname(self._dmreport_file)
            if not os.path.exists(dmreport_dir):
                os.makedirs(dmreport_dir)

            drives_list = []  # List of type string.
            json_dict = {} # Dictionary of type string value paire.
            for serial_num, drive in list(self._drvmngr_drives.items()):
                # Don't serialize drives that have no HPI data
                if drive.get_drive_enclosure() == "HPI_Data_Not_Available":
                    continue

                # Split apart the drive status into status and reason values
                # Status is first word before the first '_'
                status, reason = str(drive.get_drive_status()).split("_", 1)

                # Motr faults are passed to RAS as "EMPTY" for the status field
                if "halon" in status.lower():
                    status = "EMPTY"

                drives = {}  # Dictonary type of string key value pair
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

    def _serialize_disk_info(self):
        """Writes the current disks HPI & drivemanager data to /tmp/dcs"""
        try:
            drives_list = []
            json_dict = {}
            for serial_number, drive in list(self._hpi_drives.items()):
                # Obtain json message containing all relevant HPI data
                hpi_msg = drive.toHPIjsonMsg().getJson()
                hpi_json_msg = json.loads(hpi_msg).get("message").get("sensor_response_type").get("disk_status_hpi")

                status = "N/A"
                reason = "N/A"
                if self._drvmngr_drives.get(serial_number) is not None:
                    drive = self._drvmngr_drives[serial_number]
                    # Get the status and reason fields for the drive
                    status, reason = str(drive.get_drive_status()).split("_", 1)
                hpi_json_msg["diskStatus"] = status
                hpi_json_msg["diskReason"] = reason

                drives_list.append(hpi_json_msg)

            json_dict["timestamp"] = time.strftime("%c")
            json_dict["drives"] = drives_list
            json_dump = json.dumps(json_dict, sort_keys=True)
            with open(self._disk_info_file, "w+") as disk_info_file:
                disk_info_file.write(json_dump)

        except Exception as ae:
            logger.exception(ae)

    def _log_IEM(self, drive):
        """Sends an IEM to logging msg handler"""
        # Split apart the drive status into status and reason values
        # Status is first word before the first '_'
        status, reason = str(drive.get_drive_status()).split("_", 1)
        self._log_debug(f"_log_IEM, status: {status} reason:{reason}")

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
                logger.info(f"DiskMsgHandler, Unknown disk status/reason: {status}/{reason}")
                return

        json_data = {"enclosure_serial_number": drive.get_drive_enclosure(),
                         "disk_serial_number": drive.getSerialNumber(),
                         "slot": drive.get_drive_num(),
                         "status": status,
                         "reason": reason,
                         "hostname": self._host_id,
                         "path_id": drive.get_path_id()
                         }

        self._log_debug(f"_log_IEM, log_msg: %{log_msg}:{json.dumps(json_data, sort_keys=True)}")
        internal_json_msg = json.dumps(
                    {"actuator_request_type" : {
                        "logging": {
                            "log_level": "LOG_WARNING",
                            "log_type": "IEM",
                            "log_msg": f"{log_msg}:{json.dumps(json_data, sort_keys=True)}"
                            }
                        }
                     })

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def _check_expander_reset(self):
        """Check for expander reset by polling for sgXX changes
        DEPRECATED for drivemanager interval checks"""

        scsi_command = "ls /sys/class/enclosure/*/device/scsi_generic"
        response, error = self._run_command(scsi_command)

        # Expander reset causes scsi generic dir to vanish temporarily
        if "cannot access" in error:
            if self._scsi_generic != "N/A":
                self._scsi_generic = "N/A"
                self._transmit_expander_reset()
        else:
            # If the /dev/sgX changed then we had an expander reset
            if self._scsi_generic != "N/A" and \
               self._scsi_generic != response:
                self._transmit_expander_reset()

            self._scsi_generic = response

    def _check_drivemanager_events_interval(self):
        """Check for expander reset by examining number of drivemanager events within an interval"""
        # If the last event was more than two minutes reset everything as a safeguard against manually removed drives
        if time.time() - self._first_drivemanager_event_tm > 120:
            self._drivemanager_events_counter = 0

        # If this is the first of a set of drivemanager events then capture the timestamp
        if self._drivemanager_events_counter == 0:
            self._first_drivemanager_event_tm = time.time()

        # Increment counter to track drivemanager events for determining partial expander resets
        self._drivemanager_events_counter += 1

        logger.info(f"DiskMsgHandler, Total drivemanager events: {self._drivemanager_events_counter}")
        logger.info(f"DiskMsgHandler, Seconds since first event: {(time.time() - self._first_drivemanager_event_tm)}")

        # If max events have occurred within max interval then we have an expander reset
        if self._drivemanager_events_counter >= self._max_drivemanager_events:
            logger.info(f"DiskMsgHandler, _drivemanager_events_counter:     \
                              {self._drivemanager_events_counter} >= Max of {self._max_drivemanager_events}")

            # See if a partial expander reset has occurred which is detected by X drive events in Y seconds
            if time.time() - self._first_drivemanager_event_tm < self._max_drivemanager_event_interval:
                logger.info(f"DiskMsgHandler, Max drivemanager events occurred in {self._max_drivemanager_event_interval} seconds.")

                # Temp fix for Halon not being able to handle partial expander resets by GA
                #  When partial occurs then trigger a full expander reset and handle all 84 drives bouncing in OS
                if self._max_drivemanager_events != 84:
                    logger.info("DiskMsgHandler, Partial expander reset detected.")

                    # Reset to look for all 84 drives bouncing in the OS indicative of a full expander reset
                    self._max_drivemanager_events = 84

                    # Reset current number of drivemanager events counter
                    self._drivemanager_events_counter = 0

                    # Set max interval to two minutes for 84 drives
                    self._max_drivemanager_event_interval = 120

                    # Trigger a full expander reset when a partial has occurred
                    self._trigger_expander_reset()

                    # Log IEM and send out JSON msg
                    self._transmit_expander_reset()
                else:
                    logger.info("DiskMsgHandler, Expander reset detected.")

                    # Reset current number of drivemanager events counter
                    self._drivemanager_events_counter = 0

                    # Reset _max_drivemanager_events configurable value used to detect partial exp resets
                    self._getDM_exp_reset_values()
            else:
                logger.info(f"DiskMsgHandler, Max drivemanager events did NOT occur     \
                                                  in {self._max_drivemanager_event_interval} seconds.")

    def _transmit_expander_reset(self):
        """Create and transmit an expander reset JSON msg"""
        # Build JSON message, currently no data but following same pattern
        expanderResetMsg = ExpanderResetMsg()
        internal_json_msg = expanderResetMsg.getJson()

        # Send the json message to the RabbitMQ processor to transmit out
        self._write_internal_msgQ(RabbitMQegressProcessor.name(), internal_json_msg)

        log_msg  = "IEC: 020005001: Expander Reset Triggered"
        json_data = {"scsi_generic_device": self._scsi_generic}

        # Log an IEM
        internal_json_msg = json.dumps(
                    {"actuator_request_type" : {
                        "logging": {
                            "log_level": "LOG_WARNING",
                            "log_type": "IEM",
                            "log_msg": f"{log_msg}:{json.dumps(json_data, sort_keys=True)}"
                            }
                        }
                     })

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def _trigger_expander_reset(self):
            """Trigger an expander reset by rebooting via wbcli tool"""

            # Get the current SG device
            command : str = "ls /sys/class/enclosure/*/device/scsi_generic"

            response, error = self._run_command(command)
            if len(error) > 0:
                logger.info(f"DiskMsgHandler, SCSI Generic lookup results: {response}, {error}")

            sg_dev = f"/dev/{response}"
            command = f"sudo wbcli {sg_dev} reboot"

            response, error = self._run_command(command)
            logger.info(f"DiskMsgHandler, Expander reset triggered, results: {response}, {error}")

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()

        return response.rstrip('\n'), error.rstrip('\n')

    def _getDMreport_File(self):
        """Retrieves the file location"""
        return Conf.get(SSPL_CONF, f"{self.DISKMSGHANDLER}>{self.DMREPORT_FILE}",
                                    '/tmp/sspl/drivemanager/drive_manager.json')
    def _getDiskInfo_File(self):
        """Retrieves the file location"""
        return Conf.get(SSPL_CONF, f"{self.DISKMSGHANDLER}>{self.DISKINFO_FILE}",
                                    '/tmp/dcs/disk_info.json')
    def _getAlways_log_IEM(self):
        """Retrieves flag signifying we should always log disk status as an IEM even if they
            haven't changed.  This is useful for always logging SMART results"""
        val = bool(Conf.get(SSPL_CONF, f"{self.DISKMSGHANDLER}>{self.ALWAYS_LOG_IEM}",
                                        False))
    def _getDM_exp_reset_values(self):
        """Retrieves the values used to determine partial expander resets"""
        self._max_drivemanager_events = int(Conf.get(SSPL_CONF, f"{self.DISKMSGHANDLER}>{self.MAX_DM_EVENTS}",
                                                         14))

        self._max_drivemanager_event_interval = int(Conf.get(SSPL_CONF, f"{self.DISKMSGHANDLER}>{self.MAX_DM_EVENTS_INT}",
                                                         10))

        logger.info(f"Expander Reset will be triggered with {self._max_drivemanager_events}       \
                                            events in {self._max_drivemanager_event_interval} secs.")

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(DiskMsgHandler, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(DiskMsgHandler, self).resume()
        self._suspended = False

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
                 disk_installed = False,
                 disk_powered   = False,
                 path_id        = "N/A",
                 device_name    = "N/A"
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
        self._disk_installed = disk_installed
        self._disk_powered   = disk_powered
        self._wwn            = wwn
        self._path_id        = path_id
        self._device_name    = device_name
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
            logger.exception(f"Drive, _parse_path: {ex}, ignoring event.")
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
            logger.exception(f"Drive, _parse_path: {ex}, ignoring event.")
        return False

    def toDriveMngrJsonMsg(self, uuid =None):
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
                             self._drive_num,
                             self._disk_installed,
                             self._disk_powered)
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

    def set_disk_installed(self, disk_installed):
        """Set the disk_installed field of drive"""
        self._disk_installed = disk_installed

    def set_disk_powered(self, disk_powered):
        """Set the disk_powered field of drive"""
        self._disk_powered = disk_powered

    def set_drive_num(self, drive_num):
        """Set the drive number"""
        self._drive_num = drive_num

    def get_event_path(self):
        """Return the event path on fs"""
        return self._event_path

    def get_path_id(self):
        """Return the by-id path of drive"""
        return self._path_id

    def get_drive_status(self):
        """Return the status of the drive"""
        return self._status

    def get_drive_enclosure(self):
        """Return the enclosure of the drive"""
        return self._enclosure

    def get_disk_installed(self):
        """Return the disk_installed field of drive"""
        return self._disk_installed

    def get_disk_powered(self):
        """Return the disk_powered field of drive"""
        return self._disk_powered

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
