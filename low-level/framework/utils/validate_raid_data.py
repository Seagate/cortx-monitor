"""
 ****************************************************************************
 Filename:          validate_raid_data.py
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
import time
import sched
import subprocess
from threading import Thread
from datetime import datetime

from framework.base.sspl_constants import RaidData
from framework.utils.service_logging import logger


class RAIDSensorValidate():

    def __init__(self):
        self._scheduler = sched.scheduler(time.time, time.sleep)
        self._priority = RaidData.PRIORITY.value


    def run(self):
        # Start a new child thread validating RAID SENSOR DATA
        thread = Thread(target=self._raid_health_monitor())
        thread.daemon = True
        thread.start()

    def _raid_health_monitor(self):
        try:
            devices = RaidData.DEVICE_ARRAY.value
            raid_dir = RaidData.DIR.value
            sync_action_file = RaidData.SYNC_ACTION_FILE.value
            mismatch_cnt_file = RaidData.MISMATCH_COUNT_FILE.value
            for dev in devices:
                CHECK_COMMAND = 'echo "check" > ' + raid_dir + dev + sync_action_file
                logger.debug('Executing CHECK_COMMAND:{}'.format(CHECK_COMMAND))
                response, error = self._run_command(CHECK_COMMAND)
                if error:
                    logger.debug("Error in cmd: {} in raid health monitor"
                                .format(CHECK_COMMAND))
                while RaidData.RAID_CHECK.value:
                    STATE_COMMAND = 'cat ' + raid_dir + dev + sync_action_file
                    logger.debug('Executing STATE_COMMAND:{}'.format(STATE_COMMAND))
                    response, error = self._run_command(STATE_COMMAND)
                    output_file = self._get_unique_filename(RaidData.RAID_RESULT_FILE_PATH)
                    if response == RaidData.STATE_COMMAND_RESPONSE.value:
                        logger.debug("'Idle' found in Raid device.")
                        with open(output_file, 'w') as raid_file:
                            raid_file.write(RaidData.STATE_COMMAND_RESPONSE.value)
                        RaidData.RAID_CHECK.value = False
                        break
                    if error:
                        logger.debug("Error in cmd{}".format(STATE_COMMAND))
                        RaidData.RAID_CHECK.value = False
                MISMATCH_COUNT_COMMAND = 'cat ' + raid_dir + dev + mismatch_cnt_file
                logger.debug('Executing MISMATCH_CNT_COMMAND:{}'
                            .format(MISMATCH_CNT_COMMAND))
                response, error = self._run_command(MISMATCH_COUNT_COMMAND)
                if response == RaidData.MISMATCH_COUNT_RESPONSE.value:
                    logger.debug("No mismatch count, count is 0.")
                    with open(output_file, 'a') as raid_file:
                        raid_file.write(RaidData.MISMATCH_COUNT_RESPONSE.value)
                else:
                    logger.debug("Mismatch found!")
                if error:
                    logger.debug("Error in cmd{}".format(MISMATCH_COUNT_COMMAND))
            # Check once a week, if RAID data is corrupted.
            self._scheduler.enter(604800, self._priority, self._raid_health_monitor, ())
        except Exception as e:
            logger.exception(e)
            # Check Once a week, if RAID data is corrupted.
            self._scheduler.enter(604800, self._priority, self._raid_health_monitor, ())


    def _get_unique_filename(filename):
        unique_timestamp = datetime.now().strftime("%d-%m-%Y_%I-%M-%S-%p")
        unique_filename = filename + '_' + unique_timestamp
        return unique_filename


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