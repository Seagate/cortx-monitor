# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
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
  Description:       Validates raid data for data corruption.
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
from framework.base.sspl_constants import (COMMON_CONFIGS, RaidDataConfig,
    RaidAlertMsgs, WAIT_BEFORE_RETRY, PRODUCT_FAMILY)
from framework.utils.severity_reader import SeverityReader
from framework.utils.service_logging import logger
from framework.utils.utility import Utility

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
    SCAN_FREQUENCY = "polling_interval"
    TIMESTAMP_FILE_PATH_KEY = "timestamp_file_path"
    FAULT_ACCEPTED_TIME = "fault_accepted_time"

    # Scan for RAID integrity error every 2 weeks (1209600 seconds)
    DEFAULT_SCAN_FREQUENCY = "1209600"
    # Minimum allowed frequency for RAID integrity scans is 1 day
    # (86400 seconds ), as frequent scans affect disk i/o performance
    MIN_SCAN_FREQUENCY = 120
    DEFAULT_FAULT_ACCEPTED_TIME = "86400"
    DEFAULT_RAID_DATA_PATH = RaidDataConfig.RAID_RESULT_DIR.value
    DEFAULT_TIMESTAMP_FILE_PATH = DEFAULT_RAID_DATA_PATH + "last_execution_time"

    alert_type = None

    # alerts
    FAULT_RESOLVED = "fault_resolved"
    FAULT = "fault"
    MISSING = "missing"
    SUCCESS = "success"
    FAILED = "failed"

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
        self._fault_state = None
        self._suspended = False
        self._site_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.SITE_ID), '001')
        self._cluster_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.CLUSTER_ID), '001')
        self._rack_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.RACK_ID), '001')
        self._node_id = self._conf_reader._get_value_with_default(
                                self.SYSTEM_INFORMATION, COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.NODE_ID), '001')
        self._timestamp_file_path = self._conf_reader._get_value_with_default(
                                    self.RAIDIntegritySensor, self.TIMESTAMP_FILE_PATH_KEY, self.DEFAULT_TIMESTAMP_FILE_PATH)
        self._scan_frequency = int(self._conf_reader._get_value_with_default(
                                self.RAIDIntegritySensor, self.SCAN_FREQUENCY, self.DEFAULT_SCAN_FREQUENCY))
        self._next_scheduled_time = self._scan_frequency
        self._fault_accepted_time = int(self._conf_reader._get_value_with_default(
                                self.RAIDIntegritySensor, self.FAULT_ACCEPTED_TIME, self.DEFAULT_FAULT_ACCEPTED_TIME))

        if self._scan_frequency < self.MIN_SCAN_FREQUENCY:
            self._scan_frequency = self.MIN_SCAN_FREQUENCY

        self.utility = Utility()
        if self.utility.is_env_vm():
            self.shutdown()

        # Create DEFAULT_RAID_DATA_PATH if already not exist.
        self._create_file(self.DEFAULT_RAID_DATA_PATH)

        return True

    def read_data(self):
        return self._cache_state

    def run(self):
        """Run the sensor on its own thread"""
        # Do not proceed if module is suspended
        if self._suspended == True:
            if os.path.exists(self._timestamp_file_path):
                with open(self._timestamp_file_path, "r") as timestamp_file:
                    last_processed_log_timestamp = timestamp_file.read().strip()
                current_time = int(time.time())
                if current_time > int(last_processed_log_timestamp):
                    self._next_scheduled_time = self._scan_frequency - (current_time - int(last_processed_log_timestamp))
            logger.info("Scheduling RAID validate again after:{} seconds".format(self._next_scheduled_time))
            self._scheduler.enter(self._next_scheduled_time, self._priority, self.run, ())
            return

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        try:
            #cleanup
            self._cleanup()

            # Log RAIDIntegritySensor execution timestamp
            self._create_file(self._timestamp_file_path)
            self._log_timestamp()

            # Validate the raid data files and notify the node data msg handler
            self._raid_health_monitor()


            with open(self._timestamp_file_path, "r") as timestamp_file:
                last_processed_log_timestamp = timestamp_file.read().strip()
                current_time = int(time.time())
                if current_time > int(last_processed_log_timestamp):
                    self._next_scheduled_time = self._scan_frequency - (current_time - int(last_processed_log_timestamp))
            logger.info("Scheduling RAID validate again after:{} seconds".format(self._next_scheduled_time))
            self._scheduler.enter(self._next_scheduled_time, self._priority, self.run, ())
        except Exception as ae:
            logger.exception(ae)

    def _raid_health_monitor(self):
        try:
            devices = self._get_devices()
            if len(devices) == 0:
                return
            logger.debug("Fetched devices:{}".format(devices))

            for device in devices:
                # Update the state as 'check' for RAID device file
                result = self._update_raid_device_file(device)
                if result == "failed":
                    self._retry_execution(self._update_raid_device_file, device)
                logger.info("RAID device state is changed to 'check'")

                # Check RAID device array state is 'idle' or not
                result = self._check_raid_state(device)
                if result == "failed":
                    logger.warning("'Idle' state not found for RAID device:{}"
                                    .format(device))
                    # Retry to check RAID state
                    self._retry_execution(self._check_raid_state, device)
                logger.info("'idle' state is found in Raid device:{}."
                             .format(device))

                # Check Mismatch count in RAID device files.
                result = self._check_mismatch_count(device)
                if result == "failed":
                    # Persist RAID device fault state and send alert
                    fault_status_file = self.DEFAULT_RAID_DATA_PATH + device + "_" + RaidDataConfig.RAID_MISMATCH_FAULT_STATUS.value
                    if os.path.exists(fault_status_file):
                        with open(fault_status_file, 'r') as fs:
                            data = fs.read().rstrip()
                        data = json.loads(data)
                        if data['fault_detected_time'] != -1 and \
                           int(time.time()) - data['fault_detected_time'] > self._fault_accepted_time:

                            self.alert_type = self.FAULT
                            self._alert_msg = "Disk %s may have developed a fault, it might "\
                                "need a replacement. Please contact Seagate support" %device
                            self._send_json_msg(self.alert_type, device, self._alert_msg)
                            self._update_fault_state_file(device, self.FAULT,
                                                          fault_status_file)

                        if data['state'] == self.FAULT_RESOLVED:
                            self.alert_type = self.FAULT
                            self._alert_msg = "RAID disks present in %s RAID array, needs synchronization." %device
                            self._send_json_msg(self.alert_type, device, self._alert_msg)
                            self._update_fault_state_file(device, self.FAULT,
                                        fault_status_file, int(time.time()))
                            self._scan_frequency = self.MIN_SCAN_FREQUENCY
                    else:
                        self.alert_type = self.FAULT
                        self._alert_msg = "RAID disks present in %s RAID array, needs synchronization." %device
                        self._send_json_msg(self.alert_type, device, self._alert_msg)
                        self._update_fault_state_file(device, self.FAULT,
                                        fault_status_file, int(time.time()))
                        self._scan_frequency = self.MIN_SCAN_FREQUENCY

                    # Retry to check mismatch_cnt
                    self._retry_execution(self._check_mismatch_count, device)
                logger.debug("No mismatch count is found in Raid device:{}"
                            .format(device))

        except Exception as ae:
            logger.error("Failed in monitoring RAID health. ERROR:{}"
                         .format(str(ae)))

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
                logger.error("No RAID device found in mdstat file.")
            return device_array
        except Exception as ae:
            logger.error("Failed to get the device array. ERROR:{}"
                        .format(str(ae)))
            raise

    def _check_mismatch_count(self, device):
        try:
            status = None
            raid_dir = RaidDataConfig.DIR.value
            mismatch_cnt_file = RaidDataConfig.MISMATCH_COUNT_FILE.value
            MISMATCH_COUNT_COMMAND = 'cat ' + raid_dir + device + mismatch_cnt_file
            logger.debug('Executing MISMATCH_CNT_COMMAND:{}'
                         .format(MISMATCH_COUNT_COMMAND))
            response, error = self._run_command(MISMATCH_COUNT_COMMAND)
            if error:
                logger.error("Error in cmd{} in raid health monitor"
                            .format(MISMATCH_COUNT_COMMAND))
            if response == RaidDataConfig.MISMATCH_COUNT_RESPONSE.value:
                logger.debug("No mismatch count is found")
                status = "success"
                with open(self.output_file, 'a') as raid_file:
                    raid_file.write(RaidDataConfig.MISMATCH_COUNT_RESPONSE.value)
                fault_status_file = self.DEFAULT_RAID_DATA_PATH + device + "_"+ RaidDataConfig.RAID_MISMATCH_FAULT_STATUS.value
                if os.path.exists(fault_status_file):
                    with open(fault_status_file, 'r') as fs:
                        data = fs.read().rstrip()
                    data = json.loads(data)
                    if data['state'] == self.FAULT:
                        faulty_device = data['device']
                        if device == faulty_device:
                            self.alert_type = self.FAULT_RESOLVED
                            self._alert_msg = "RAID disks present in %s RAID array are synchronized." %device
                            self._send_json_msg(self.alert_type, device, self._alert_msg)
                            self._update_fault_state_file(device, self.FAULT_RESOLVED, fault_status_file)
                            self._scan_frequency = int(self._conf_reader._get_value_with_default(
                                self.RAIDIntegritySensor, self.SCAN_FREQUENCY, self.DEFAULT_SCAN_FREQUENCY))
                            self._scan_frequency = max(self._scan_frequency,
                                                         self.MIN_SCAN_FREQUENCY)
            else:
                status = "failed"
                logger.debug("Mismatch found in {} file in raid_integrity_data!"
                             .format(mismatch_cnt_file))
            return status
        except Exception as ae:
            logger.error("Failed in checking mismatch_cnt in RAID file. ERROR:{}"
                         .format(str(ae)))
            raise

    def _check_raid_state(self, device):
        try:
            status = None
            raid_check = 0
            raid_dir = RaidDataConfig.DIR.value
            sync_action_file = RaidDataConfig.SYNC_ACTION_FILE.value
            while raid_check <= RaidDataConfig.MAX_RETRIES.value:
                self.output_file = self._get_unique_filename(RaidDataConfig.RAID_RESULT_FILE_PATH.value, device)
                STATE_COMMAND = 'cat ' + raid_dir + device + sync_action_file
                logger.debug('Executing STATE_COMMAND:{}'.format(STATE_COMMAND))
                response, error = self._run_command(STATE_COMMAND)
                if error:
                    logger.warn("Error in cmd{} in raid health monitor"
                                .format(STATE_COMMAND))
                    raid_check += 1
                else:
                    if response == RaidDataConfig.STATE_COMMAND_RESPONSE.value:
                        status = "success"
                        with open(self.output_file, 'w') as raid_file:
                            raid_file.write(RaidDataConfig.STATE_COMMAND_RESPONSE.value + "\n")
                        break
                    else:
                        status = "failed"
                        raid_check += 1
                        time.sleep(WAIT_BEFORE_RETRY)
            return status
        except Exception as ae:
            logger.error("Failed in checking RAID device state. ERROR:{}"
                        .format(str(ae)))
            raise

    def _update_raid_device_file(self, device):
        try:
            status = "failed"
            raid_check = 0
            raid_dir = RaidDataConfig.DIR.value
            sync_action_file = RaidDataConfig.SYNC_ACTION_FILE.value
            while raid_check <= RaidDataConfig.MAX_RETRIES.value:
                CHECK_COMMAND = "echo 'check' |sudo tee " + raid_dir + device + sync_action_file + " > /dev/null"
                logger.debug('Executing CHECK_COMMAND:{}'.format(CHECK_COMMAND))
                response, error = self._run_command(CHECK_COMMAND)
                if error:
                    logger.warn("Failed in executing command:{}."
                                .format(error))
                    raid_check += 1
                    time.sleep(1)
                else:
                    logger.debug("RAID device state is changed to 'check' with response : {}".format(response))
                    status = "success"
                    break
            return status
        except Exception as ae:
            logger.error("Failed to update RAID File. ERROR:{}"
                         .format(str(ae)))
            raise

    def _retry_execution(self, function_call, device):
        while True:
            logger.debug("Executing function:{} after {} time interval"
                         .format(function_call, RaidDataConfig.NEXT_ITERATION_TIME.value))
            time.sleep(RaidDataConfig.NEXT_ITERATION_TIME.value)
            result = function_call(device)
            if result == self.SUCCESS:
                return

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
                "event_time": epoch_time,
                "description": error_msg
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

    def _create_file(self, path):
        dir_path = path[:path.rindex("/")]
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)
            logger.debug("{} in creation of dir path : {}".format(self.SUCCESS, dir_path))
        if not os.path.exists(path):
            file = open(path, "w+")
            file.close()


    def _log_timestamp(self):
        current_time = str(int(time.time()))
        with open(self._timestamp_file_path, "w") as timestamp_file:
            timestamp_file.write(current_time)

    def _update_fault_state_file(self, device, fstate, fault_state_file,
                                 fault_detected_time=-1):
        self._fault_state = fstate
        data = {
            'device' : device,
            'state' : fstate,
            'fault_detected_time' : fault_detected_time,
        }
        self._create_file(fault_state_file)
        with open(fault_state_file, 'w') as fs:
            fs.write(json.dumps(data))

    def _cleanup(self):
        """Clean up the validate raid result files"""
        if os.path.exists(self._timestamp_file_path):
            os.remove(self._timestamp_file_path)
        path = RaidDataConfig.RAID_RESULT_DIR.value
        if os.path.exists(path):
            current_time = time.time()
            result_files = [file for file in os.listdir(path) if file.endswith(".txt")]
            for file in result_files:
                if os.path.getmtime(os.path.join(path, file)) < (current_time - 24*60*60):
                    if os.path.isfile(os.path.join(path, file)):
                        os.remove(os.path.join(path, file))

