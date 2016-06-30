"""
 ****************************************************************************
 Filename:          hpi_actuator.py
 Description:       Handles messages for changing state in Resource Data
                    Records(RDR) within HPI's Resource Presence Table(RPT)
 Creation Date:     4/05/2016
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************

 Example JSON msgs for getting/setting disk LED state:
    "node_controller": {
        "node_request": "LED: get [drive id]"
    }

    "node_controller": {
        "node_request": "LED: set [drive id]  [Possible Control States]"
    }
    
    [Possible Control States] can be one of
        FAULT_ON, FAULT_OFF, IDENTIFY_ON, IDENTIFY_OFF,
        PULSE_SLOW_ON, PULSE_SLOW_OFF, PULSE_FAST_ON, PULSE_FAST_OFF
        
 Example JSON msgs for getting/setting disk power state:
    "node_controller": {
        "node_request": "DISK: get [drive id]"
    }

    "node_controller": {
        "node_request": "DISK: set [drive id] [POWER_ON / POWEROFF]"
    }

 Example JSON msgs for getting/setting enclosure ID:
    "node_controller": {
        "node_request": "ENCL: get id [drive id]"
    }

    "node_controller": {
        "node_request": "ENCL: set id [drive id] [0-99]"
    }


    [drive id] can be Device Name like /dev/sdab or disk Serial Number

    A200 Drive LED Handling Doc
    https://docs.google.com/document/d/16_-9ja8KgHUW5g3ewuIiXSAr6mI_DBdOygX4fJcgHrc/edit#heading=h.1v0tagyghqat
"""

import os
import subprocess

from zope.interface import implements
from actuators.Ihpi import IHPI

from framework.base.debug import Debug
from framework.utils.service_logging import logger

from xrtx_hpi_lib.hpi_session_management import PyHpiSessionManagement

from openhpi_baselib import SA_OK, SaHpiCtrlStateT, SaHpiCtrlStateUnionT, \
        HpiUtilGen, saHpiControlSet

from hpi.inventory.iterator import FruIterator, SubFruIterator
from hpi.inventory.parser.inventory import SystemInventoryParser
from hpi.inventory.system import SystemInventory
from hpi.resource.entry_tree import ResourceEntityTree


class HPIactuator(Debug):
    """Handles messages for changing state in Resource Data
       Records(RDR) within HPI's Resource Present Table(RPT)"""

    implements(IHPI)

    ACTUATOR_NAME = "HPIactuator"

    VALID_CTRL_STATES = ["FAULT_ON", "FAULT_OFF", "IDENTIFY_ON", 
                         "IDENTIFY_OFF", "PULSE_SLOW_ON", "PULSE_SLOW_OFF", 
                         "PULSE_FAST_ON", "PULSE_FAST_OFF",
                         "POWER_ON", "POWER_OFF"]

    @staticmethod
    def name():
        """ @return: name of the module."""
        return HPIactuator.ACTUATOR_NAME

    def __init__(self, conf_reader):
        super(HPIactuator, self).__init__()

        # Session mgmt to re-discover and use an existing HPI session
        self._session_mgmt = PyHpiSessionManagement(logger)
        self._session_id = None

        # set or get request
        self._command_type = "N/A"

        # For set commands, the desired control state to set the RDR
        self._control_state = "N/A"

        # Drive number used in entity type {DISK_BAY,X}
        self._drive_number = -1

        # Read in the configuration values, for possible future use
        #self._conf_reader = conf_reader
        #self._read_config()

        # Temporarily leave debugging on during beta release     
        self._set_debug(True)
        self._set_debug_persist(True)

    def perform_request(self, jsonMsg):
        """Performs the HPI request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        try:
            # Parse the incoming json msg into usable fields
            error = self._parse_json(jsonMsg)
            if error != "None":
                return error

            # Find the ControlRecord id to use based on the requested ctrl state
            ctrlrec_name = self._get_ctrlrec_name()
            self._log_debug("ctrlrec_name: %s" % ctrlrec_name)
            if "Error" in ctrlrec_name:
                return ctrlrec_name

            # Create the HPI system info
            hpi_tree_root = self._get_sysinfo()
            if hpi_tree_root == os.EX_SOFTWARE:
                return "Error: Unable to parse fetch system information"

            # Search through the HPI tree for the desired ControlRecord
            system_inventory = SystemInventory(hpi_tree_root)
            for encl in system_inventory:
                # TODO: Match incoming enclosure s/n for multiple enclosures
                serial_number = encl.serial_number()

                self._log_debug("Enclosure[{}]:".format(serial_number))
                self._log_debug("  Type: {}".format(encl.enclosure_type()))
                for item in encl.product_information():
                    self._log_debug("    {}: {}".format(item.name(), item.value()))

                # Retrieve the ControlRecord using python-hpi library
                control_record = self._get_ctrl_record("Disk",
                                    SubFruIterator(encl.disk_drives()), ctrlrec_name)
                if control_record is None:
                    return "Error: Failed to find ControlRecord in HPI tree"
                # Used in returned response for get requests
                value = control_record.value()

            # Set the ControlRecord to the desired value
            if self._command_type == "set":
                response = self._set_control_record(control_record)
                if "Error" in response:
                    return response
                value = self._control_state

            # Successful get/set on ControlRecord
            response = "Success, Name: {} Ctrl Num: {}, Mode: {}, Value: {}" \
                        .format(ctrlrec_name,
                                control_record.record_number(),
                                control_record.mode(), value)

        except Exception as e:
            logger.exception(e)
            response = "Error: {0}".format(str(e))

        return response

    def _get_ctrl_record(self, fru_type, fru_node, ctrlrec_name):
        """Traverse the HPI tree for the desired ControlRecord

        @return control_record: The ControlRecord
        """
        # Search thru the HPI tree for the desired disk number
        for fru_index, fru_obj in fru_node:
            if int(fru_index) == int(self._drive_number):
                self._log_debug("     {}[{}]".format(fru_type, fru_index))
                # Search for the ControlRecord RDR and return it
                for fru in fru_obj:
                    if ctrlrec_name in fru.name():
                        self._log_debug("       Name: {}".format(fru.name()))
                        self._log_debug("      {}".format(fru))
                        return fru
        return None

    def _set_control_record(self, control_record):
        """Set the ControlRecord to the desired value"""

        # Create a ctrl state object with state union
        state = SaHpiCtrlStateT()
        state.Type = control_record.data_type()
        state.StateUnion = SaHpiCtrlStateUnionT()

        # Set the value to be set TODO: Handle other types besides just Digital
        state.StateUnion.Digital = HpiUtilGen.toSaHpiCtrlStateDigitalT(self._control_state)

        response = "Success"
        try:
            # Open a session and make the API call
            error = self._session_mgmt.OpenSession()
            if error != SA_OK:
                return "Error: saHpiSessionOpen: {}".format(HpiUtilGen.fromSaErrorT(error))

            # Call the ctrl set HPI API to set the state and verify success
            error = saHpiControlSet(self._session_mgmt.sid, control_record.rid(),
                                    control_record.record_number(),
                                    control_record.mode(),
                                    state)
            if error != SA_OK:
                response = "Error: Cannot set ControlRecord state: {}" \
                            .format(HpiUtilGen.fromSaErrorT(error))

        except Exception as e:
            logger.exception(e)
            response = "Error: {}".format(str(e))

        finally:
            # Close HPI session
            error = self._session_mgmt.CloseSession()
            if error != SA_OK:
                response = "Error: saHpiSessionClose: {}" \
                            .format(HpiUtilGen.fromSaErrorT(error))

        # Return the result for setting state of the ControlRecord
        return response

    def _get_sysinfo(self):
        """Get the HPI system inventory and parse

        @return hpi_tree_root: root of the HPI tree
        """
        inventory = SystemInventoryParser()
        hpi_tree_root = inventory.parse()

        if hpi_tree_root is False:
            return os.EX_SOFTWARE
        return hpi_tree_root

    def _get_ctrlrec_name(self):
        """Determines the ControlRecord ID to use for the requested control state
           and simplifies on/off/pulse states from parsed json msg"""

        if self._control_state == "FAULT_ON" or \
           self._control_state == "FAULT_OFF" or \
           self._control_state == "N/A":            # if not stated then defaults to "fault LED" for now

            if "ON" in self._control_state:
                self._control_state = "ON"
            else:
                self._control_state = "OFF"
            # ControlRecord ID for fault LED
            return "rqst_fault"

        elif self._control_state == "IDENTIFY_ON" or \
             self._control_state == "IDENTIFY_OFF":

            if "ON" in self._control_state:
                self._control_state = "ON"
            else:
                self._control_state = "OFF"
            # ControlRecord ID for identify LED
            return "rqst_ident"

        elif self._control_state == "PULSE_SLOW_ON" or \
             self._control_state == "PULSE_SLOW_OFF":

            if "ON" in self._control_state:
                self._control_state = "PULSE_ON"
            else:
                self._control_state = "PULSE_OFF"
            # ControlRecord ID for slow pulse LED
            return "rqst_in_crit_array"

        elif self._control_state == "PULSE_FAST_ON" or \
             self._control_state == "PULSE_FAST_OFF":

            if "ON" in self._control_state:
                self._control_state = "PULSE_ON"
            else:
                self._control_state = "PULSE_OFF"
            # ControlRecord ID for fast pulse LED
            return "rqst_in_failed_array"

        elif self._control_state == "POWER_ON" or \
             self._control_state == "POWER_OFF":

            # Looks conflicting but we're actually setting DEVICE_OFF to OFF to turn it on
            if "ON" in self._control_state:
                self._control_state = "OFF"
            else:
                self._control_state = "ON"
            # ControlRecord ID for powering on/off a drive
            return "device_off"

        return "Error: Invalid control state: %s" % self._control_state

    def _parse_json(self, jsonMsg):
        """Parse the json message into usable fields"""

        # Reinitialize variables
        self._command_type  = "N/A"
        self._control_state = "N/A"
        self._drive_number  = -1

        # Parse out the node request to perform
        node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
        self._log_debug("perform_request, node_request: %s" % node_request)

        # Separate the fields into usable params
        # [0]:Component [1]:get/set [2]: identifier like disk s/n [3]: Ctrl State 
        params = node_request.strip().split(" ")
        self._log_debug("perform_request, params: %s" % str(params))

        # Parse out get/set request
        self._command_type = params[1].lower()
        self._log_debug("perform_request, command_type: %s" % self._command_type)
        if self._command_type not in ["set", "get"]:
           self._log_debug("perform_request, Invalid command_type! Not 'set' or 'get'")
           return "Error: Invalid command type: %s" % self._command_type

        # Parse out the drive to apply command and retrieve the drive number
        drive_request = params[2]
        self._log_debug("perform_request, drive to apply command: %s" % drive_request)
        error = self._get_drive_num(drive_request)
        if error != "None":
            return error

        # Parse out the requested control state and verify it is supported
        if self._command_type == "set":
            self._control_state = params[3].upper()
            error = self._validate_control_state()
            if error != "None":
                return error

        # No errors occurred during parsing of json msg
        return "None"

    def _validate_control_state(self):
        """Verify that the requested control state is valid"""
        self._log_debug("perform_request, requested control state: %s" % self._control_state)
        if self._control_state not in HPIactuator.VALID_CTRL_STATES:
            return "Error: {} must be {}".format(self._control_state, VALID_CTRL_STATES)
        return "None"

    def _get_drive_num(self, drive_request):
        """Determine the drive number from the serial number or device name in msg"""
        # Get the serial number of the drive if the device name was used in command
        if drive_request.startswith("/"):
            command = "sudo /usr/sbin/hdparm -I {0} | grep 'Serial Number:'".format(drive_request)
            response, error = self._run_command(command)
            if error:
                return "Error: {0}".format(str(error))

            serial_num = response.strip().split(" ")[-1]
        else:
            serial_num = drive_request
        self._log_debug("perform_request, drive serial number: %s" % serial_num)

        # Recursively grep through the drivemanager dir with the serial number and get the path
        command = "grep -R {0} /tmp/dcs/dmreport/* --exclude=/tmp/dcs/dmreport/drive_manager.json" \
                     .format(serial_num)
        response, error = self._run_command(command)
        if error:
            return "Error: {0}".format(str(error))

        # Parse out the drive number found in the drivemanager path to be used
        self._drive_number = os.path.dirname(response).split("/")[-1]
        self._log_debug("perform_request, drive number: %s" % self._drive_number)

        if len(self._drive_number) == 0 or \
           self._drive_number == -1:
            return "Error: Failed to lookup disk number in /tmp/dcs/dmreport. (System still initializing?)"

        return "None"

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        self._log_debug("run_command, executing command: %s" % command)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()

        return response.rstrip('\n'), error.rstrip('\n')