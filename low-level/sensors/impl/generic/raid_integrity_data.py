"""
 ****************************************************************************
 Filename:          raid_integrity_data.py
 Description:       Validates raid data for data corruption.
 Creation Date:     07/08/2020
 Author:            Amol Shinde

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
import socket
import uuid

from datetime import datetime

from framework.base.module_thread import SensorThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.sspl_constants import COMMON_CONFIGS, RaidDataConfig, RaidAlertMsgs, WAIT_BEFORE_RETRY
from framework.utils.severity_reader import SeverityReader
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from message_handlers.node_data_msg_handler import NodeDataMsgHandler

from zope.interface import implementer
from sensors.Iraid import IRAIDsensor

@implementer(IRAIDsensor)
class RAIDIntegritySensor(SensorThread, InternalMsgQ):


    SENSOR_NAME       = "RAIDIntegritySensor"
    PRIORITY          = 1
    RESOURCE_TYPE     = "node:os:raid_integrity"

    # Section and keys in configuration file
    RAIDIntegritySensor = SENSOR_NAME.upper()

    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "site_id"
    CLUSTER_ID = "cluster_id"
    NODE_ID = "node_id"
    RACK_ID = "rack_id"
    POLLING_INTERVAL = "polling_interval"

    # check once a week, the integrity of raid data
    DEFAULT_POLLING_INTERVAL = "604800"

    alert_type = None

    # alerts
    FAULT_RESOLVED = "fault_resolved"
    FAULT = "fault"
    MISSING = "missing"

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return RAIDIntegritySensor.SENSOR_NAME

    def __init__(self):
        super(RAIDIntegritySensor, self).__init__(self.SENSOR_NAME,
                                         self.PRIORITY)
        self._cache_state = None

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(RAIDIntegritySensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(RAIDIntegritySensor, self).initialize_msgQ(msgQlist)
        
        self._alert_msg = None
        self._alert_resolved = True
        self._suspended = False
        self._site_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.SITE_ID), '001')
        self._cluster_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.CLUSTER_ID), '001')
        self._rack_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.RACK_ID), '001')
        self._node_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.NODE_ID), '001')  
        self._polling_interval = int(self._conf_reader._get_value_with_default(
                                self.RAIDIntegritySensor, self.POLLING_INTERVAL, self.DEFAULT_POLLING_INTERVAL))
        return True

    def read_data(self):
        return self._cache_state

    def run(self):
        """Run the sensor on its own thread"""

        # Do not proceed if module is suspended
        if self._suspended == True:
            logger.info("Scheduling RAID vaidate again")
            self._scheduler.enter(self._polling_interval, self._priority, self.run, ())
            return

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        try:
            #cleanup
            self._cleanup()

            # Validate the raid data files and notify the node data msg handler
            self._raid_health_monitor()

            logger.info("Scheduling RAID vaidate again")
            self._scheduler.enter(self._polling_interval, self._priority, self.run, ())
        except Exception as ae:
            logger.exception(ae)

    def _raid_health_monitor(self):
        try:
            devices = self._get_devices()
            logger.debug("Fetched devices:{}".format(devices))
            raid_check = 0
            raid_dir = RaidDataConfig.DIR.value
            sync_action_file = RaidDataConfig.SYNC_ACTION_FILE.value
            mismatch_cnt_file = RaidDataConfig.MISMATCH_COUNT_FILE.value
            for device in devices:
                CHECK_COMMAND = "sudo echo 'check' > " + raid_dir + device + sync_action_file
                logger.debug('Executing CHECK_COMMAND:{}'.format(CHECK_COMMAND))
                response, error = self._run_command(CHECK_COMMAND)
                if error:
                    logger.error("Error in cmd: {} in raid health monitor"
                                .format(CHECK_COMMAND))
                else:
                    while raid_check <= RaidDataConfig.MAX_RETRIES.value:
                        STATE_COMMAND = 'cat ' + raid_dir + device + sync_action_file
                        logger.debug('Executing STATE_COMMAND:{}'.format(STATE_COMMAND))
                        response, error = self._run_command(STATE_COMMAND)
                        output_file = self._get_unique_filename(RaidDataConfig.RAID_RESULT_FILE_PATH.value, device)
                        if response == RaidDataConfig.STATE_COMMAND_RESPONSE.value:
                            logger.debug("'idle' state is found in Raid device:{}.".format(device))
                            with open(output_file, 'w') as raid_file:
                                raid_file.write(RaidDataConfig.STATE_COMMAND_RESPONSE.value + "\n")
                            break
                        else:
                            raid_check += 1
                            time.sleep(WAIT_BEFORE_RETRY)
                        if error:
                            logger.warn("Error in cmd{} in raid health monitor"
                                        .format(STATE_COMMAND))
                            raid_check += 1

                    if raid_check > RaidDataConfig.MAX_RETRIES.value:
                        self._alert_resolved = False
                        self.alert_type = self.FAULT
                        self._alert_msg = RaidAlertMsgs.STATE_MSG.value
                        self._send_json_msg(self.alert_type, device, self._alert_msg)

                    MISMATCH_COUNT_COMMAND = 'cat ' + raid_dir + device + mismatch_cnt_file
                    logger.debug('Executing MISMATCH_CNT_COMMAND:{}'
                                .format(MISMATCH_COUNT_COMMAND))
                    response, error = self._run_command(MISMATCH_COUNT_COMMAND)
                    if response == RaidDataConfig.MISMATCH_COUNT_RESPONSE.value:
                        logger.debug("No mismatch count is found")
                        with open(output_file, 'a') as raid_file:
                            raid_file.write(RaidDataConfig.MISMATCH_COUNT_RESPONSE.value)
                    else:
                        logger.debug("Mismatch found in {} file in raid_integrity_data!"
                                    .format(mismatch_cnt_file))
                        self._alert_resolved = False
                        self.alert_type = self.FAULT
                        self._alert_msg = RaidAlertMsgs.MISMATCH_MSG.value
                        self._send_json_msg(self.alert_type, device, self._alert_msg)
                    if error:
                        logger.error("Error in cmd{} in raid health monitor"
                                    .format(MISMATCH_COUNT_COMMAND))

                if self._alert_resolved:
                    self.alert_type = self.FAULT_RESOLVED
                    self._alert_msg = None
                    self._send_json_msg(self.alert_type, device, self._alert_msg)

        except Exception as ae:
            logger.error(ae)

    def _get_devices(self):
        try:
            mdstat_file = RaidDataConfig.MDSTAT_FILE.value
            with open (mdstat_file, 'r') as fp:
                content = fp.readlines()
            device_array = []
            for line in content:
                if "active" in line:
                    device = line.split(":")[0].rstrip()
                    device_array.append(device)
            if len(device_array) == 0:
                self._alert_resolved = False
                self.alert_type = self.MISSING
                device = "N/A"
                self._alert_msg = "No Device Found"
                self._send_json_msg(self.alert_type, device, self._alert_msg)
            return device_array
        except Exception as ae:
            logger.error("Failed to get the device array. ERROR:{}"
                        .format(str(ae)))
            raise

    def _get_unique_filename(self, filename, device):
        unique_timestamp = datetime.now().strftime("%d-%m-%Y_%I-%M-%S-%p")
        unique_filename = f"{filename}_{device}_{unique_timestamp}.txt"
        return unique_filename

    def _send_json_msg(self, alert_type, resource_id, error_msg):
        """Transmit data to NodeDataMsgHandler to be processed and sent out"""

        epoch_time = str(int(time.time()))
        severity_reader = SeverityReader()
        severity = severity_reader.map_severity(alert_type)
        self._alert_id = self._get_alert_id(epoch_time)
        host_name = socket.getfqdn()

        info = {
                "site_id": self._site_id,
                "cluster_id": self._cluster_id,
                "rack_id": self._rack_id,
                "node_id": self._node_id,
                "resource_type": self.RESOURCE_TYPE,
                "resource_id": resource_id,
                "event_time": epoch_time
               }
        specific_info = {
            "error": error_msg
                }

        internal_json_msg = json.dumps(
            {"sensor_request_type" : {
                "node_data": {
                    "status": "update",
                    "sensor_type" : "node:os:raid_integrity",
                    "host_id": host_name,
                    "alert_type": alert_type,
                    "alert_id": self._alert_id,
                    "severity": severity,
                    "info": info,
                    "specific_info": specific_info
                    }
                }
            })
        self.alert_type = None

        logger.debug("_send_json_msg, internal_json_msg: %s" %(internal_json_msg))

        # Send the event to node data message handler to generate json message and send out
        self._write_internal_msgQ(NodeDataMsgHandler.name(), internal_json_msg)

    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
        epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(RAIDIntegritySensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(RAIDIntegritySensor, self).resume()
        self._suspended = False

    def _run_command(self, command):
        """Run the command and get the response and error returned"""
        logger.debug(f"_run_command: {command}")
        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        response, error = process.communicate()

        if response:
            logger.debug(f"_run_command, response: {str(response)}")
        if error:
            logger.debug(f"_run_command: error: {str(error)}")

        return response.decode().rstrip('\n'), error.decode().rstrip('\n')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(RAIDIntegritySensor, self).shutdown()

    def _cleanup(self):
        """Clean up the validate raid result files"""
        path = RaidDataConfig.RAID_RESULT_DIR.value
        current_time = time.time()
        result_files = [file for file in os.listdir(path) if file.endswith(".txt")]
        for file in result_files:
            if os.path.getmtime(os.path.join(path, file)) < (current_time - 24*60*60) :
                if os.path.isfile(os.path.join(path, file)):
                    os.remove(os.path.join(path, file))
