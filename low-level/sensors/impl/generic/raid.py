"""
 ****************************************************************************
 Filename:          raid.py
 Description:       Monitors /proc/mdstat for changes and notifies
                    the node_data_msg_handler when a change is detected
 Creation Date:     07/16/2015
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
import subprocess

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from message_handlers.node_data_msg_handler import NodeDataMsgHandler

from zope.interface import implements
from sensors.Iraid import IRAIDsensor


class RAIDsensor(ScheduledModuleThread, InternalMsgQ):

    implements(IRAIDsensor)

    SENSOR_NAME       = "RAIDsensor"
    PRIORITY          = 1

    # Section and keys in configuration file
    RAIDSENSOR        = SENSOR_NAME.upper()
    RAID_STATUS_FILE  = 'RAID_status_file'


    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RAIDsensor.SENSOR_NAME

    def __init__(self):
        super(RAIDsensor, self).__init__(self.SENSOR_NAME,
                                         self.PRIORITY)
        # Current RAID status information
        self._RAID_status = None

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RAIDsensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RAIDsensor, self).initialize_msgQ(msgQlist)

        self._RAID_status_file = self._get_RAID_status_file()
        logger.info("         Monitoring RAID status file: %s" % self._RAID_status_file)

    def read_data(self):
        """Return the Current RAID status information"""
        return self._RAID_status

    def run(self):
        """Run the sensor on its own thread"""

        # Allow systemd to process all the drives so we can map device name to serial numbers
        time.sleep(90)

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        #self._set_debug(True)
        #self._set_debug_persist(True)

        try:
            # Check for a change in status file and notify the node data msg handler
            self._notify_NodeDataMsgHandler()
        except Exception as ae:
            logger.exception(ae)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Fire every 30 seconds to see if there's a change in RAID status file
        self._scheduler.enter(30, self._priority, self.run, ())

    def _notify_NodeDataMsgHandler(self):
        """See if the status files changed and notify node data message handler
            for generating JSON message"""
        if not os.path.isfile(self._RAID_status_file):
            logger.warn("status_file: %s does not exist, ignoring." % self._RAID_status_file)
            return

        # Read in status and see if it has changed
        with open(self._RAID_status_file, "r") as datafile:
            status = datafile.read()

        # Do nothing if the RAID status has not changed
        if self._RAID_status == status:
            self._log_debug("_notify_NodeDataMsgHandler status unchanged, ignoring: %s" % status)
            return

        # Update the RAID status
        self._RAID_status = status

        # Parse out drive serial numbers being used and transmit json msg
        self._get_drive_sn()

    def _send_json_msg(self):
        """Transmit data to NodeDataMsgHandler to be processed and sent out"""

        # Convert device names to serial numbers
        drive_0 = self._run_hdparm_command(self._drive_0)
        drive_1 = self._run_hdparm_command(self._drive_1)
        self._log_debug("_get_drive_sn, device: %s, drive 0: %s, drive 1: %s" % \
                        (self._device, drive_0, drive_1))

        internal_json_msg = json.dumps(
            {"sensor_request_type" : {
                "node_data" : {
                    "sensor_type" : "raid_data",
                    "status"  : self._mdstat,
                    "device"  : self._device,
                    "drive_0" : drive_0,
                    "drive_1" : drive_1,
                    }
                }
            })

        # Send the event to node data message handler to generate json message and send out
        self._write_internal_msgQ(NodeDataMsgHandler.name(), internal_json_msg)

        # Reset values in case there are more entries to be processed in /proc/mdstats
        self._drive_0 = "N/A"
        self._drive_1 = "N/A"
        self._device  = "N/A"

    def _get_drive_sn(self):
        """Parse out the two drives used by mdraid
            look up their serial numbers and return them"""
        # Replace new line chars with spaces
        self._mdstat = self._RAID_status.strip().replace("\n", " ")

        # Break the status string apart into separate fields
        fields = self._mdstat.split(" ")

        self._drive_0 = "N/A"
        self._drive_1 = "N/A"
        self._device  = "N/A"
        # Look for '[0]' & '[1]' identifying the drives in raid array
        for field in fields:
            if "[0]" in field:
                self._drive_0 = "/dev/{}".format(field[: field.find('[')])
            elif "[1]" in field:
                self._drive_1 = "/dev/{}".format(field[: field.find('[')])
            elif "md" in field:
                self._device = "/dev/{}".format(field)

            # Transmit data in a json msg if all the fields are filled in
            if self._drive_0 != "N/A" and \
               self._drive_1 != "N/A" and \
               self._device  != "N/A":
                self._send_json_msg()

    def _run_hdparm_command(self, drive):
        """Run the hdparm command and get the response and error returned"""
        command = "sudo /usr/sbin/hdparm -I {0} | grep 'Serial Number:'".format(drive)
        self._log_debug("_run_hdparm_command, executing: %s" % command)

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()
        if not error:
            return response.strip().split(" ")[-1]
        else:
            return drive

    def _get_RAID_status_file(self):
        """Retrieves the file containing the RAID status information"""
        return self._conf_reader._get_value_with_default(self.RAIDSENSOR,
                                                        self.RAID_STATUS_FILE,
                                                        '/proc/mdstat')
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RAIDsensor, self).shutdown()
