"""
 ****************************************************************************
 Filename:          SMR_drive_data.py
 Description:       Reads state and polling time values from each drive and 
                    logs them to journal
 Creation Date:     10/05/2015
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
import ctypes
import fcntl
import subprocess

from sensors.impl.c_api.ATA_SG_IO import AtaCmd, SgioHdr 

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from systemd import journal

# Modules that receive messages from this module
from message_handlers.node_data_msg_handler import NodeDataMsgHandler

from zope.interface import implements
from sensors.INode_data import INodeData

libc = ctypes.CDLL('libc.so.6')

class SMRdriveData(ScheduledModuleThread, InternalMsgQ):

    implements(INodeData)

    SENSOR_NAME       = "SMRdriveData"
    PRIORITY          = 1

    # Section and keys in configuration file
    SMRDRIVEDATA      = SENSOR_NAME.upper()
    LOGGING_INTERVAL  = 'logging_interval'


    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return SMRdriveData.SENSOR_NAME

    def __init__(self):
        super(SMRdriveData, self).__init__(self.SENSOR_NAME,
                                         self.PRIORITY)
        self._cache_state = None

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(SMRdriveData, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(SMRdriveData, self).initialize_msgQ(msgQlist)

        self._set_debug(True)
        self._set_debug_persist(True)

        self._get_config()

    def read_data(self):
        """Return the Current Cache information"""
        return self._cache_state

    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        # Slight pause so we don't clutter up logs with other threads initializing
        time.sleep(80)

        try:
            # Loop thru all the devices starting with an sg
            command = "ls /dev/sg*"
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.PIPE)
            stdout, err = process.communicate()
            dirs = stdout.splitlines()

            # Send the ATA command to retrieve values from the drives and log them
            for dir in dirs: 
                self._send_ATA_command(dir)

        except Exception as ae:
            logger.exception(ae)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        # Schedule the next time to run thread
        self._scheduler.enter(self._logging_interval, self._priority, self.run, ())

    def _send_ATA_command(self, dev):
        """Send ATA commands to retrieve values"""

        # Based on document:
        # https://drive.google.com/a/seagate.com/file/d/0B2-I_uIzpoyFbXlYT2UzQ0Z4aG5EVWoyajVYWXVvX01ValRV/view
        page_number = 4
        log_addr    = 0x30

        ata_cmd = AtaCmd(opcode=0x85,  # ATA PASS-THROUGH (16)
                   protocol=(4 << 1),  # PIO Data-In
                   # flags field
                   # OFF_LINE = 0 (0 seconds offline)
                   # CK_COND = 1 (copy sense data in response)
                   # T_DIR = 1 (transfer from the ATA device)
                   # BYT_BLOK = 1 (length is in blocks, not bytes)
                   # T_LENGTH = 2 (transfer length in the SECTOR_COUNT field)
                   flags=0x2e,
                   features_filler=0,
                   features=0,
                   sector_count_filler=0,
                   sector_count=1,
		           lba_low_filler=0,
                   lba_low=log_addr,
                   lba_mid_filler=(page_number >> 8) & 0xff,
                   lba_mid=page_number & 0xff,  
                   lba_high_filler=0,
                   lba_high=0,      
                   device=0,
                   command=0x2f,  # ATA_READ_LOG_EXT 0x2f
                   control=0)

        ASCII_S = 83
        SG_DXFER_FROM_DEV = -3
        sense  = ctypes.create_string_buffer(64)
        result = ctypes.create_string_buffer(512)

        # Create an SG_IO Header object to be sent that points to the ATA command
        sgio = SgioHdr(interface_id=ASCII_S,
                       dxfer_direction=SG_DXFER_FROM_DEV,
                       cmd_len=ctypes.sizeof(ata_cmd),
                       mx_sb_len=ctypes.sizeof(sense),
                       iovec_count=0,
                       dxfer_len=ctypes.sizeof(result),
                       dxferp=ctypes.cast(result, ctypes.c_void_p),
                       cmdp=ctypes.addressof(ata_cmd),
                       sbp=ctypes.cast(sense, ctypes.c_void_p),
                       timeout=3000,
                       flags=0, pack_id=0, usr_ptr=None, status=0, masked_status=0,
                       msg_status=0, sb_len_wr=0, host_status=0, driver_status=0,
                       resid=0, duration=0, info=0)
        SG_IO = 0x2285  # <scsi/sg.h>

        try:
            with open(dev, 'r') as fd:
                if libc.ioctl(fd.fileno(), SG_IO, ctypes.byref(sgio)) != 0:
                    self._log_debug(" _send_ATA_command dev: %s does not support ATA command, skipping" % dev)
                    return

                orig_row = result[64:80]
                valid = "%02x%02x" % (ord(orig_row[15]), ord(orig_row[14]))

                # Only care about valid values
                if valid != "8000":
                    return

                # Swap bytes in the raw data 
                swap_row = "{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}{}".format(
                           orig_row[1], orig_row[0], orig_row[3], orig_row[2], 
                           orig_row[5], orig_row[4], orig_row[7], orig_row[6],
                           orig_row[9], orig_row[8], orig_row[11], orig_row[10],
                           orig_row[13], orig_row[12], orig_row[15], orig_row[14])

                # Create a string to log for debugging purposes
                i     = 1
                res   = ""
                for bb in swap_row:
                    if i % 2 == 0:
                        res += ("%02x " % ord(bb))
                    else:
                        res += ("%02x" % ord(bb))
                    i += 1

                # Start with last four bytes, fist two are unused of the four
                steady_state = "%02x%02x" % (ord(swap_row[10]), ord(swap_row[11]))
                polling_tm   = "%02x%02x" % (ord(swap_row[12]), ord(swap_row[13]))
                if len(dev) == 8:
                    msg = "{} : {} state:{}h time:{}h valid:{}h" \
                          .format(dev, res, steady_state, polling_tm, valid)
                else:
                    msg = "{}: {} state:{}h time:{}h valid:{}h" \
                          .format(dev, res, steady_state, polling_tm, valid)
                journal.send(msg, SYSLOG_IDENTIFIER="sspl-ll")

                # Assign the shortest drive polling time to the thread scheduler
                if int(polling_tm, 16) < self.logging_interval and \
                   int(polling_tm, 16) != 0:
                    self.logging_interval = int(polling_tm, 16)

        except Exception:
	        pass # Does not support ATA command so ignore this device

    def _get_config(self):
        """Retrieves the information in /etc/sspl_ll.conf"""
        self._logging_interval = int(self._conf_reader._get_value_with_default(self.SMRDRIVEDATA,
                                                        self.LOGGING_INTERVAL,
                                                        3600))
        logger.info("logging_interval: %s" % self._logging_interval)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(SMRdriveData, self).shutdown()
