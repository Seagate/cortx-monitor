"""
 ****************************************************************************
 Filename:          hpi.py
 Description:       Handles messages for changing state in Resource Data
                    Records(RDR) within HPI's Resource Present Table(RPT)
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

    [drive id] can be Device Name like /dev/sdab or disk Serial Number

    [Possible Control States] can be one of
        FAULT_ON, FAULT_OFF, IDENTIFY_ON, IDENTIFY_OFF,
        PULSE_SLOW_ON, PULSE_SLOW_OFF, PULSE_FAST_ON, PULSE_FAST_OFF

    A200 Drive LED Handling Doc
    https://docs.google.com/document/d/16_-9ja8KgHUW5g3ewuIiXSAr6mI_DBdOygX4fJcgHrc/edit#heading=h.1v0tagyghqat
"""

import os
import subprocess
from openhpi_baselib import *

from zope.interface import implements
from actuators.Ihpi import IHPI

from framework.base.debug import Debug
from framework.utils.service_logging import logger


class HPI(Debug):
    """Handles messages for changing state in Resource Data
       Records(RDR) within HPI's Resource Present Table(RPT)"""

    implements(IHPI)

    ACTUATOR_NAME = "HPI"


    @staticmethod
    def name():
        """ @return: name of the module."""
        return HPI.ACTUATOR_NAME

    def __init__(self, conf_reader):
        super(HPI, self).__init__()

        # set or get request 
        self._command_type = "N/A"

        # For set commands, the desired control state to set the RDR
        self._control_state = "N/A"

        # Drive number used in entity type {DISK_BAY,X}
        self._drive_number = -1

        # Read in the configuration values, for possible future use
        #self._conf_reader = conf_reader
        #self._read_config()

        # Temporarily leave debugging on during beta releases       
        self._set_debug(True)
        self._set_debug_persist(True)

    def perform_request(self, jsonMsg):
        """Performs the HPI request

        @return: The response string from performing the request
        """
        self._check_debug(jsonMsg)

        response = "N/A"
        sid = None
        try:
            error = self._parse_json(jsonMsg)
            if error != "":
                return error

            # Obtain session ID to openhpi
            error, sid = saHpiSessionOpen(SAHPI_UNSPECIFIED_DOMAIN_ID, None)
            if error != SA_OK:
                return "Error: saHpiSessionOpen: %s" % HpiUtilGen.fromSaErrorT(error)

            # Update HPI Resource Present Table (RPT)
            error = saHpiDiscover(sid)
            if error != SA_OK:
                return "saHpiDiscover: %s" % HpiUtilGen.fromSaErrorT(error)

            # Create the entity ID
            entity_type = "DISK_BAY,{}".format(self._drive_number)
            self._log_debug("entity_type: %s" % entity_type)

            # find the RDR ID to use for the desired control state
            rdr_id = self._get_rdr_id()
            self._log_debug("rdr_id: %s" % rdr_id)

            response = self._discover_domain(sid, entity_type, rdr_id)
            self._log_debug("response: %s" % response)

        except Exception as e:
            logger.exception(e)
            response = "Error: {0}".format(str(e))

        finally:
            # Close HPI session
            error = saHpiSessionClose(sid)
            if error != SA_OK:
                response = "Error: saHpiSessionClose: %s" % HpiUtilGen.fromSaErrorT(error)

        return response

    def _get_rdr_id(self):
        """Determines the RDR ID to use for the desired control state
           and simplifies on/off/pulse states from parsed json msg"""

        if self._control_state == "FAULT_ON" or \
           self._control_state == "FAULT_OFF" or \
           self._control_state == "N/A":            # if not stated then defaults to "fault LED" for now
   
            if "ON" in self._control_state:
                self._control_state = "ON"
            else:
                self._control_state = "OFF"

            return "RQST FAULT"

        elif self._control_state == "IDENTIFY_ON" or \
             self._control_state == "IDENTIFY_OFF":

            if "ON" in self._control_state:
                self._control_state = "ON"
            else:
                self._control_state = "OFF"

            return "RQST IDENT"

        elif self._control_state == "PULSE_SLOW_ON" or \
             self._control_state == "PULSE_SLOW_OFF":

            if "ON" in self._control_state:
                self._control_state = "PULSE_ON"
            else:
                self._control_state = "PULSE_OFF"

            return "RQST IN CRIT ARRAY"

        elif self._control_state == "PULSE_FAST_ON" or \
             self._control_state == "PULSE_FAST_OFF":

            if "ON" in self._control_state:
                self._control_state = "PULSE_ON"
            else:
                self._control_state = "PULSE_OFF"
    
            return "RQST IN FAILED ARRAY"

        return "ERROR: Invalid control state: %s" % self._control_state
        
    def _discover_domain(self, sid, entity_type, rdr_id):
        """Discover HPI domain by looping thru Resource Present Table(RPT)
           to find the entity type, ie {DISK_BAY,0} then set the ctrl state
           of the Resource Data Record(RDR), ie RQST FAULT for solid LED

           Entity Types for disks are in the form of 
            {DISK_BAY,X} where X is the disk number

           Current RDR IDs have the following effects
            'RQST FAULT' = Solid Fault LED 
            'RQST IN CRIT ARRAY' = PULSE Slow   (rate TBD)
            'RQST IN FAILED ARRAY' = PULSE Fast (rate TBD)
            'RQST IDENT' = Solid Identify LED

           Possible Control States used from parsed json
           FAULT_ON, FAULT_OFF, IDENTIFY_ON, IDENTIFY_OFF,
           PULSE_SLOW_ON, PULSE_SLOW_OFF, PULSE_FAST_ON, PULSE_FAST_OFF
        """

        found = 0
        nextid = SAHPI_FIRST_ENTRY
        res = SaHpiRptEntryT()

        # Loop thru the existing HPI Resource Present Table(RPT) 
        #  until the correct entity_type is located
        while nextid != SAHPI_LAST_ENTRY:
            currid = nextid

            # Get the current RPT entry
            error, nextid, res = saHpiRptEntryGet(sid, currid)
            if error != SA_OK:
                    return "Error: saHpiRptEntryGet: %s" % HpiUtilGen.fromSaErrorT(error)

            if (not(res.ResourceCapabilities & SAHPI_CAPABILITY_RDR) or
                not(res.ResourceCapabilities & SAHPI_CAPABILITY_CONTROL) or
                not(entity_type in HpiUtil.fromSaHpiEntityPathT(res.ResourceEntity))):
                    continue

            nextid2 = SAHPI_FIRST_ENTRY
            rid = res.ResourceId
            rdr = SaHpiRdrT()

            # Loop thru the Resource Data Records(RDRs) of the RPT
            #  until the correct RDR is located by it's ID
            while nextid2 != SAHPI_LAST_ENTRY:
                currid2 = nextid2
                error, nextid2, rdr = saHpiRdrGet(sid, rid, currid2)
                if error != SA_OK:
                        return "Error: saHpiRdrGet: %s" % HpiUtilGen.fromSaErrorT(error)

                # Currently only care about control records, skip others
                if rdr.RdrType != SAHPI_CTRL_RDR:
                        continue

                # Only care about OEM records and the one matching the RDR ID
                if (rdr.RdrTypeUnion.CtrlRec.OutputType != SAHPI_CTRL_OEM or
                    not(rdr_id in rdr.IdString.Data)):
                        continue

                self._log_debug("_discover_domain, ResourceEntity: %s" % 
                            HpiUtil.fromSaHpiEntityPathT(res.ResourceEntity))

                if self._command_type == "set":
                     response = self._disk_control_set(sid, rid, rdr, rdr_id)
                else:
                    response = self._disk_control_get(sid, rid, rdr, rdr_id)

                found += 1

        if found == 0:
            response = 'Error: No HPI controllable disks found.'

        self._log_debug("_discover_domain, response: %s" % response)
        return response

    def _disk_control_get(self, sid, rid, rdr, rdr_id):
        """Get the ctrl state of the disk's RDR"""

        # Get the ctrl record and number of the RDR
        ctrl_rec = rdr.RdrTypeUnion.CtrlRec
        ctrl_num = ctrl_rec.Num

        # Create a ctrl state data structure with union and initialize
        state = SaHpiCtrlStateT()
        state.Type = SAHPI_CTRL_TYPE_DIGITAL
        state.StateUnion = SaHpiCtrlStateUnionT()
        state.StateUnion.Digital = SAHPI_CTRL_LED

        # Call the ctrl get HPI API to get the state and verify success
        error, mode, state = saHpiControlGet(sid, rid, ctrl_num, state)
        if error != SA_OK:
            return "Error: Cannot get disk state: %s" % HpiUtilGen.fromSaErrorT(error)
        else:
            return "Success: Ctrl Num: %d, Id: %s, Mode: %s State: %s" % \
                    (ctrl_num, rdr_id, 
                     HpiUtilGen.fromSaHpiCtrlModeT(mode), 
                     HpiUtilGen.fromSaHpiCtrlStateDigitalT(state.StateUnion.Digital))

    def _disk_control_set(self, sid, rid, rdr, rdr_id):
        """Set the ctrl state of the disk's Resource Data Record (RDR)"""

        # Get the ctrl record and verify that it's digital only
        ctrl_rec = rdr.RdrTypeUnion.CtrlRec
        if ctrl_rec.Type != SAHPI_CTRL_TYPE_DIGITAL:
                return "Cannot handle non digital disk controls!"

        # Get the ctrl number of the RDR
        ctrl_num = ctrl_rec.Num
        mode = SAHPI_CTRL_MODE_MANUAL

        # Create a ctrl state data structure with union
        state = SaHpiCtrlStateT()
        state.Type = SAHPI_CTRL_TYPE_DIGITAL
        state.StateUnion = SaHpiCtrlStateUnionT()

        # Convert the on, off, pulse_on, pulse_off to global const values
        state.StateUnion.Digital = HpiUtilGen.toSaHpiCtrlStateDigitalT(self._control_state)

        # Call the ctrl set HPI API to set the state and verify success
        error = saHpiControlSet(sid, rid, ctrl_num, mode, state)
        if error != SA_OK:
            return "Error: Cannot set disk state or mode: (%s, %s)" % \
                       (HpiUtilGen.fromSaErrorT(error), mode)
        else:
            return "Success: Ctrl Num: %d, Id: %s, Mode: %s State: %s" % \
                    (ctrl_num, rdr_id, 
                     HpiUtilGen.fromSaHpiCtrlModeT(mode), 
                     HpiUtilGen.fromSaHpiCtrlStateDigitalT(state.StateUnion.Digital))

    def _parse_json(self, jsonMsg):
        """Parse the json message into usable fields"""

        # Reinitialize variables
        self._command_type = "N/A"
        self._control_state = "N/A"
        self._drive_number = -1

        # Parse out the node request to perform
        node_request = jsonMsg.get("actuator_request_type").get("node_controller").get("node_request")
        self._log_debug("perform_request, node_request: %s" % node_request)

        params = node_request.strip().split(" ")
        self._log_debug("perform_request, params: %s" % str(params))

        # Parse out get/set request
        self._command_type = params[1].lower()
        self._log_debug("perform_request, command_type: %s" % self._command_type)
        if self._command_type not in ["set", "get"]:
           self._log_debug("perform_request, Invalid command_type! Not 'set' or 'get'")
           return "Error: Invalid command type: %s" % self._command_type

        # Parse out the drive to apply command
        drive_request = params[2]
        self._log_debug("perform_request, drive to apply command: %s" % drive_request)

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

        # Parse out command to apply
        if self._command_type == "set":
            self._control_state = params[3].upper()
            self._log_debug("perform_request, requested control state: %s" % self._control_state)

            if self._control_state not in ["FAULT_ON", "FAULT_OFF", "IDENTIFY_ON", 
                                           "IDENTIFY_OFF", "PULSE_SLOW_ON", "PULSE_SLOW_OFF", 
                                           "PULSE_FAST_ON", "PULSE_FAST_OFF"]:
                return "Error: %s must be FAULT_ON, FAULT_OFF, IDENTIFY_ON, IDENTIFY_OFF," \
                        "PULSE_SLOW_ON, PULSE_SLOW_OFF, PULSE_FAST_ON, PULSE_FAST_OFF" \
                        .format(self._control_state)
        return ""

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        self._log_debug("run_command, executing command: %s" % command)
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()

        return response.rstrip('\n'), error.rstrip('\n')