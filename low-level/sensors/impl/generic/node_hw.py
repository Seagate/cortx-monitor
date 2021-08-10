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
  Description:       Fetches Server FRUs and Logical Sensor data using inband IPMI interface to BMC
 ****************************************************************************
"""

import calendar
import json
import os
import re
import subprocess
import time
import uuid
from collections import namedtuple
from zope.interface import implementer

from framework.base.debug import Debug
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import SensorThread
from framework.base.sspl_constants import (
    DATA_PATH, BMCInterface, PRODUCT_FAMILY, ServiceTypes, node_key_id)
from framework.utils import encryptor
from framework.utils.conf_utils import (
    GLOBAL_CONF, IP, SECRET, SSPL_CONF, BMC_INTERFACE, BMC_CHANNEL_IF,
    USER, Conf, NODE_ID_KEY, BMC_IP_KEY, BMC_USER_KEY, BMC_SECRET_KEY,
    MACHINE_ID, NODEHWSENSOR, IPMI_CLIENT)
from framework.utils.config_reader import ConfigReader
from framework.utils.service_logging import logger
from framework.utils.severity_reader import SeverityReader
from framework.utils.store_factory import file_store
from framework.utils.iem import Iem
from framework.utils.os_utils import OSUtils
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from sensors.INode_hw import INodeHWsensor
from framework.utils.ipmi_client import IpmiFactory
from sensors.impl.generic.node_hw_alerts_info import alert_for_event

# bash exit codes
BASH_ILLEGAL_CMD = 127

# Override default store
store = file_store

CACHE_DIR_NAME = f"{DATA_PATH}server"

BMC_CHANNEL = namedtuple(
    'BMC_CHANNEL', 'alert description impact recommendation')
INACTIVE_CHANNEL = BMC_CHANNEL(
    "fault", "Server BMC is unreachable through {} interface.",
    "IPMITOOL commands can not be executed through BMC {} interface.",
    "Verify BMC IP, username and password is correct,"
    " Enable {} interface.")
ACTIVE_CHANNEL = BMC_CHANNEL(
    "fault_resolved", "Server BMC is reachable through {} interface.",
    "IPMITOOL commands can be executed through BMC {} interface.", "NA"
)

system = BMCInterface.SYSTEM.value
lan_cache_path = BMCInterface.LAN_IF_CACHE.value
system_cache_path = BMCInterface.SYSTEM_IF_CACHE.value
active_bmc_if_cache = BMCInterface.ACTIVE_BMC_IF.value


@implementer(INodeHWsensor)
class NodeHWsensor(SensorThread, InternalMsgQ):
    """Obtains data about the FRUs and logical sensors and updates
       if any state change occurs"""


    SENSOR_NAME = "NodeHWsensor"
    PRIORITY = 1


    sel_event_info = ""

    TYPE_PSU_SUPPLY = 'Power Supply'
    TYPE_PSU_UNIT = 'Power Unit'
    TYPE_FAN = 'Fan'
    TYPE_DISK = 'Drive Slot / Bay'
    TYPE_TEMPERATURE = "Temperature"
    TYPE_VOLTAGE = "Voltage"
    TYPE_CURRENT = "Current"

    fru_map = {
        "Drive Slot / Bay": "disk",
        "Fan": "fan",
        "Power Supply": "psu",
        "Power Unit": "psu"
    }


    SEL_USAGE_THRESHOLD = 90
    SEL_INFO_PERC_USED = "Percent Used"
    SEL_INFO_FREESPACE = "Free Space"
    SEL_INFO_ENTRIES = "Entries"

    # This file stores the last index from the SEL list for which we have issued an event.
    INDEX_FILE = "last_sel_index"
    LIST_FILE  = "sel_list"
    LIST_FILE_COLLECT = "sel_list_collect"

    UPDATE_CREATE_MODE = "w+"
    UPDATE_ONLY_MODE   = "r+"

    IPMI_SDR_ERR = "command failed"

    CHANNEL_INFO = {}

    LAN_CHANNEL_INFO = {
        "Channel Medium Type": "802.3 LAN", "Channel Protocol Type": "IPMB-1.0",
        "Session Support": "multi-session", "Active Session Count": "1",
        "Protocol Vendor ID": "7154", "Alerting": "enabled",
        "Per_message Auth": "enabled", "User Level Auth": "enabled",
        "Access Mode": "always available"}

    KCS_CHANNEL_INFO = {
        "Channel Medium Type": "System Interface", "Channel Protocol Type": "KCS",
        "Session Support": "session-less", "Active Session Count": "0",
        "Protocol Vendor ID": "7154"}

    channel_err = False

    sdr_reset_required = False
    request_shutdown = False
    sel_last_queried = None
    SEL_QUERY_FREQ = 300

    POLLING_INTERVAL = "polling_interval"
    DEFAULT_POLLING_INTERVAL = "30"

    IPMITOOL = "sudo ipmitool "
    IPMISIMTOOL = "ipmisimtool "

    DYNAMIC_KEYS = {
            "Sensor Reading",
            "States Asserted",
            }

    # Dependency list
    DEPENDENCIES = {
                    "plugins": ["NodeDataMsgHandler"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """@return: name of the module."""
        return NodeHWsensor.SENSOR_NAME

    def __init__(self):
        super(NodeHWsensor, self).__init__(self.SENSOR_NAME.upper(), self.PRIORITY)
        self.os_utils = OSUtils()
        self.host_id = self.os_utils.get_fqdn()

        self.fru_types = {
            self.TYPE_FAN: self._parse_fan_info,
            self.TYPE_PSU_SUPPLY: self._parse_psu_supply_info,
            self.TYPE_PSU_UNIT: self._parse_psu_unit_info,
            self.TYPE_DISK: self._parse_disk_info,
            self.TYPE_TEMPERATURE: self._parse_temperature_info,
            self.TYPE_VOLTAGE: self._parse_voltage_info,
            self.TYPE_CURRENT: self._parse_current_info,
        }
        self.faulty_resources = {}

        # Flag to indicate suspension of module
        self._suspended = False

        # Validate configuration file for required valid values
        try:
            self.conf_reader = ConfigReader()

        except (IOError, ConfigReader.Error) as err:
            logger.error("[ Error ] when validating the config file {0} - {1}"\
                 .format(self.CONF_FILE, err))
        self.polling_interval = \
            int(Conf.get(SSPL_CONF, f"{NODEHWSENSOR}>{self.POLLING_INTERVAL}",
                         self.DEFAULT_POLLING_INTERVAL))

    def _get_file(self, name):
        if os.path.exists(name):
            mode = self.UPDATE_ONLY_MODE
        else:
            mode = self.UPDATE_CREATE_MODE
        return open(name, mode)

    def _initialize_cache(self):
        if not os.path.exists(CACHE_DIR_NAME):
            logger.info(f"Creating cache dir: {CACHE_DIR_NAME}")
            os.makedirs(CACHE_DIR_NAME)
        logger.info(f"Using cache dir: {CACHE_DIR_NAME}")

        # Get the stored previous alert info
        self.faulty_resources_path = os.path.join(CACHE_DIR_NAME,
            f'faulty_resources_{self._node_id}')
        self.faulty_resources = store.get(self.faulty_resources_path)
        if self.faulty_resources is None:
            self.faulty_resources = {}
            store.put(self.faulty_resources, self.faulty_resources_path)

        self.index_file_name = os.path.join(CACHE_DIR_NAME, self.INDEX_FILE)

        bad_index_file = \
                not os.path.exists(self.index_file_name) or \
                os.path.getsize(self.index_file_name) == 0
        if bad_index_file:
            self._write_index_file(0)
        # Now self.index_file has a valid sel index in it

        self.list_file_name = os.path.join(CACHE_DIR_NAME, self.LIST_FILE)
        self.list_file = self._get_file(self.list_file_name)

        self.list_file_collect_name = os.path.join(CACHE_DIR_NAME, self.LIST_FILE_COLLECT)

    def _write_index_file(self, index):
        if not isinstance(index, int):
            index = int(index, base=16)
        literal = "{0:x}\n".format(index)

        with self._get_file(self.index_file_name) as index_file :
            index_file.seek(0)
            index_file.truncate()
            index_file.write(literal)
            index_file.flush()

    def _read_index_file(self):
        with self._get_file(self.index_file_name) as index_file :
            index_file.seek(0)
            index_line = index_file.readline().strip()
            return int(index_line, base=16)

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(NodeHWsensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(NodeHWsensor, self).initialize_msgQ(msgQlist)

        ipmi_client_name = Conf.get(SSPL_CONF, f"{NODEHWSENSOR}>{IPMI_CLIENT}",
                                    "ipmitool")
        self.ipmi_client = IpmiFactory().get_implementor(ipmi_client_name)

        self._node_id = Conf.get(GLOBAL_CONF, NODE_ID_KEY,'SN01')
        self._bmc_user = Conf.get(GLOBAL_CONF, BMC_USER_KEY, 'ADMIN')
        _bmc_secret = Conf.get(GLOBAL_CONF, BMC_SECRET_KEY, 'ADMIN')
        self._bmc_ip = Conf.get(GLOBAL_CONF, BMC_IP_KEY, '')

        self._channel_interface = Conf.get(
            SSPL_CONF, f"{BMC_INTERFACE}>{BMC_CHANNEL_IF}", 'system')
        self.active_bmc_if = None
        # To avoid raising duplicate alerts, check if alert already
        # exists for supported interface by reading persistent cache value.
        self.get_interface_from_cache()

        self.iem = Iem()
        self.iem.check_existing_fault_iems()
        self.IPMI = self.iem.EVENT_CODE["IPMITOOL_AVAILABLE"][1]
        if self._channel_interface in BMCInterface.LAN_IF.value:
            try:
                # Decrypt bmc secret
                decryption_key = encryptor.gen_key(
                    MACHINE_ID, ServiceTypes.SERVER_NODE.value)
                self._bmc_passwd = encryptor.decrypt(
                    decryption_key, _bmc_secret, self.SENSOR_NAME)
            except Exception as err:
                logger.critical(f"BMC password decryption failed due to {err},"
                    "NodeHWSensor monitoring disabled.")
                self.shutdown()

        # Set flag 'request_shutdown' to true if ipmitool/simulator is non-functional
        _, _, retcode = self._run_ipmitool_subcommand("sel info")
        if retcode != 0 and self.channel_err:
            if self._channel_interface == system:
                log_msg = (
                    "ipmitool commands not able to access BMC through"
                    " configured %s interface." % self._channel_interface)
            else:
                log_msg = (
                    "ipmitool commands not able to access BMC through"
                    " configured %s interface or even fallback option"
                    " 'KCS' interface." % (self._channel_interface))
            logger.critical(log_msg)
            self.request_shutdown = True
        else:
            self._initialize_cache()
            self._fetch_channel_info()
            if self.channel_err is False:
                self._read_sensor_list()

        return True

    @staticmethod
    def check_cache_exists(path):
        exists, _ = store.exists(path)
        return exists

    def get_interface_from_cache(self):
        """Read the data from persistent cache."""
        self.lan_fault = None
        self.system_fault = None

        # To avoid raising duplicate alerts/to monitor fault_resolved alert
        # after reboot, check if alert already exists for supported
        # interface by reading persistent cache value.
        for key in BMCInterface.SUPPORTED_BMC_IF.value:
            if (key in BMCInterface.LAN_IF.value and
                    self.check_cache_exists(lan_cache_path)):
                self.lan_fault = store.get(lan_cache_path)
                if isinstance(self.lan_fault, bytes):
                    self.lan_fault = self.lan_fault.decode()
            elif key == system and self.check_cache_exists(system_cache_path):
                self.system_fault = store.get(system_cache_path)
                if isinstance(self.system_fault, bytes):
                    self.system_fault = self.system_fault.decode()
        # Read BMC active_interface value from cache.
        # In case of lan/lanplus fault, we fallback to system(KCS).
        # If lan_fault="fault" and persistent cache for active_bmc_if exists
        # read active_bmc_if value from cache otherwise read from config.
        if self.check_cache_exists(active_bmc_if_cache) and self.lan_fault == "fault":
            self.active_bmc_if = store.get(active_bmc_if_cache)
            if isinstance(self.active_bmc_if, bytes):
                self.active_bmc_if = self.active_bmc_if.decode()
        else:
            self.active_bmc_if = self._channel_interface
            store.put(self.active_bmc_if, active_bmc_if_cache)

    def _fetch_channel_info(self):
        """Fetch channel information."""
        # fetch bmc interface (KCS or LAN)  information
        command = None
        res, _, retcode = self._run_ipmitool_subcommand("channel info")
        if retcode == 0:
            channel_info = res.strip().split("\n")
            # convert channel_info into dict
            channel_info = {k.strip():v.strip() for k,v in (x.split(":") for x in channel_info[1:]\
                            if ":" in x)}
            self.CHANNEL_INFO = channel_info

        # check for lan/lanplus fault resolved alert
        if self.lan_fault == "fault":
            command = BMCInterface.LAN_CMD.value.format(
                    self._channel_interface, self._bmc_ip, self._bmc_user,
                    self._bmc_passwd)
            command = " ".join([self.IPMITOOL, command, "channel info"])
            res, retcode = self._run_command(command)
            if retcode == 0:
                self.get_channel_alert(ACTIVE_CHANNEL, self._channel_interface)

    def _update_list_file(self):
        with open(self.list_file_collect_name, self.UPDATE_CREATE_MODE) as f:
            # make sel list filter only for available frus. no extra data needed
            # 'Power Supply|Power Unit|Fan|Drive Slot / Bay'
            f.seek(0)
            f.truncate()
            available_fru = '|'.join(self.fru_types.keys())
            _, err, retcode = self._run_ipmitool_subcommand(
                    "sel list", grep_args=f"{available_fru}",
                    out_file=f)
            if retcode != 0:
                msg = f"ipmitool sel list command failed: {err}"
                logger.error(msg)
                raise Exception(msg)

        # os.rename() is required to be atomic on POSIX,
        # (from here: https://docs.python.org/2/library/os.html#os.rename)
        # which means that even if the current python process crashes
        # the SEL list in the self.list_file_name file
        # will always be in a consistent state.
        os.rename(self.list_file_collect_name, self.list_file_name)

        self.list_file.close()
        self.list_file = self._get_file(self.list_file_name)

    def _check_and_clear_sel(self):
        """ Clear SEL Table if SEL used memory seen above threshold
            SEL_USAGE_THRESHOLD """

        info_dict = {}

        if self.sel_last_queried:
            last_checked = time.time() - self.sel_last_queried

            if last_checked < self.SEL_QUERY_FREQ:
                return

        try:
            sel_info, err, retcode = self._run_ipmitool_subcommand("sel info")
            if retcode != 0:
                logger.error(f"ipmitool sel info command failed,  \
                    with err {err}")
                return (False)

            # record SEL last queried time
            self.sel_last_queried = time.time()

            key = val = None
            info_list = sel_info.split("\n")

            for info in info_list:
                if ':' in info:
                    key, val = [f.strip() for f in info.split(":", 1)]
                    info_dict[key] = val

            if self.SEL_INFO_PERC_USED in info_dict:
                '''strip '%' or any unwanted char from value'''
                info_dict[self.SEL_INFO_PERC_USED] = re.sub('%', '',
                                          info_dict[self.SEL_INFO_PERC_USED])

                if info_dict[self.SEL_INFO_PERC_USED].isdigit():
                   used = int(info_dict[self.SEL_INFO_PERC_USED])
                else:
                    entries = int(info_dict[self.SEL_INFO_ENTRIES])
                    free = int(re.sub('[A-Za-z]+','',\
                               info_dict[self.SEL_INFO_FREESPACE]))

                    entries = entries * 16
                    free = free + entries

                    used = (100 * entries) / free
                    logger.debug(f"SEL % Used: calculated {used}%")

            if used > self.SEL_USAGE_THRESHOLD:
                logger.warning(f"SEL usage above threshold {self.SEL_USAGE_THRESHOLD}%, \
                    clearing SEL")

                _, err, retcode = self._run_ipmitool_subcommand("sel clear")
                if retcode != 0:
                    logger.critical(f"{self.host_id}: Error in clearing SEL, overflow"
                        " may result in loss of node alerts from SEL in future")
                    return

                #reset last processed SEL index in cached index file
                self._write_index_file(0)

        except Exception as ae:
            logger.exception(ae)

    def _read_sensor_list(self):
        self.sensor_id_map = dict()
        for fru in self.fru_types:
            self.sensor_id_map[fru] = { sensor_num: sensor_id
                for (sensor_id, sensor_num) in
                self._get_sensor_list_by_type(fru)}

    def run(self):
        """Run the sensor on its own thread"""
        # Do not proceed if module is suspended
        if self._suspended == True:
            self._scheduler.enter(self.polling_interval, self._priority, self.run, ())
            return
        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        if self.request_shutdown is False:
            try:
                # check BMC interface is accessible or not
                if self.channel_err or self.lan_fault == "fault":
                    self._fetch_channel_info()

                # Reset sensor_map_id after ipmi simulation
                if not os.path.exists("%s/activate_ipmisimtool"
                    % CACHE_DIR_NAME):
                    # Sensor numbers set by ipmisimtool would cause key lookup
                    # failure with actual ipmitool SDRs. So sensor_map_id needs
                    # to be refreshed with current SDRs.
                    if self.sdr_reset_required:
                        if self.channel_err is False:
                            self.sdr_reset_required = False
                            self._read_sensor_list()

                if self.channel_err is False:
                    # Check for a change in ipmi sel list and notify the node data
                    # msg handler
                    if os.path.getsize(self.list_file_name) != 0:
                        # If the SEL list file is not empty, that means that some
                        # of the processing from the last iteration is incomplete.
                        # Complete that before getting the new SEL events.
                        self._notify_NodeDataMsgHandler()

                    self._update_list_file()
                    self._notify_NodeDataMsgHandler()

                    try:
                        self._check_faulty_resource_status()
                    except Exception as e:
                        logger.error("Direct check for faulty resources recovery "
                            "failed with error %s" % e)

                self._check_and_clear_sel()
            except Exception as ae:
                logger.exception(ae)

            # Reset debug mode if persistence is not enabled
            self._disable_debug_if_persist_false()
            self._scheduler.enter(self.polling_interval, self._priority, self.run, ())
        else:
            logger.warning(f"{self.SENSOR_NAME} Node hw monitoring disabled")
            self.shutdown()

    def _check_faulty_resource_status(self):
        # Currently, the SSPL sensor relies on IPMI SEL events to track server
        # resources fault & recovery. However, its been observed multiple times
        # with Supermicro servers, that SEL not getting updated in case recoveries
        # of some resources.
        # So sensor additionally polling faulty or missing resources, in addition
        # to current polling for SEL.

        # Copying object to avoid RuntimeError: dictionary changed size during iteration
        faulty_res = self.faulty_resources.copy()
        for sensor_id in faulty_res:
            dynamic, static = self._get_sensor_sdr_props(sensor_id)
            if dynamic and 'States Asserted' in dynamic:
                #  'States Asserted': 'Power Supply, Presence detected'
                resource_state = re.sub(',  +', ', ', re.sub('[\[\]]','',
                    dynamic['States Asserted']).replace('\n',','))
                sensor_status = resource_state.split(',')
                sensor_status = sensor_status[0] if len(sensor_status) == 1 \
                    else sensor_status[1]
                sensor_status = sensor_status.strip()
                if sensor_status in ["", "Presence detected"]:
                    self._generate_resource_alert(sensor_id, faulty_res)
            elif static and 'Assertion Events' in static \
                and 'Status' in static:
                # 'Status': 'ok'
                # 'Assertion Events': ''
                if static['Assertion Events'] in [""] \
                    and static['Status'] == 'ok':
                    self._generate_resource_alert(sensor_id, faulty_res)
        del faulty_res

    def _generate_resource_alert(self, sensor_id, faulty_res):
        status = faulty_res[sensor_id]['status'].lower()
        status = 'Deasserted' if status == 'asserted' else 'Asserted'
        event = faulty_res[sensor_id]['event']
        if event.lower().endswith(("going high", "going low")):
            threshold_old = event.split(" ")[-1]
            threshold_new = ' high' if threshold_old == 'low' else ' low'
            event = event.replace(f" {threshold_old}", threshold_new)
        date = time.strftime("%m/%d/%Y")
        event_time = time.strftime("%H:%M:%S")
        device_id = faulty_res[sensor_id]['device_id']
        device_type, sensor_num = NodeHWsensor._get_device_type_num(device_id)
        is_last = True
        index = 0
        logger.warn("Found missing entry in the IPMI SEL for resource '%s' & "
            "event '%s'. Generating resource event alert directly" % (sensor_id, event))
        try:
            self.fru_types[faulty_res[sensor_id]['fru_type']](index,
                date, event_time, device_id, sensor_num, event, status, is_last)
        except KeyError:
            logger.warn(f"Sensor {sensor_num} for {device_type} is not present, ignoring event")
        except Exception as e:
            logger.error(f"_generate_resource_alert, error {e} while processing \
                sel_event: {(index, date, event_time, device_id, device_type, sensor_num, event, status)}, ignoring event")

    def _get_sel_event(self):
        last_index = self._read_index_file()

        # TODO: See if the following 2 loops can be reduced to
        # a single loop using mmap() and a fixed file format like
        # the one produced by the 'ipmitool sel file' or
        # 'ipmitool sel writeraw' commands.
        found = False
        self.list_file.seek(0, os.SEEK_SET)
        for line in self.list_file:
            if not found:
                if line.split("|")[0].strip() == "{0:x}".format(last_index):
                    found = True
                continue

            yield self._make_sel_event(line)

        if not found:
            # This can mean one of a few things:
            # 1. The SEL has been cleared beyond the last index we saw
            # 2. It has rotated to beyond the last index we saw
            # 3. self.list_file is empty
            self.list_file.seek(0, os.SEEK_SET)
            for line in self.list_file:
                yield self._make_sel_event(line)

    def _make_sel_event(self, sel_line):
        # Separate out the components of the sel event
        # Sample sel event which gets parsed
        # 2 | 04/16/2019 | 05:29:09 | Fan #0x30 | Lower Non-critical going low  | Asserted
        index, date, _time, device_id, event, status = [
            attr.strip() for attr in sel_line.split("|") ]
        device_type, sensor_num = NodeHWsensor._get_device_type_num(device_id)

        return (index, date, _time, device_id, device_type, sensor_num, event, status)

    @staticmethod
    def _get_device_type_num(device_id):
        try:
            device_type, sensor_num = re.match(
                    '(.*) (#0x([0-9a-f]+))?', device_id).group(1, 3)
        except:
            # If device_type and sensor_num is not found in device_id
            device_type = device_id
            sensor_num = ''

        return device_type, sensor_num

    def _notify_NodeDataMsgHandler(self):
        """See if there is any new event gets generated in the sel and notify
            node data message handler for generating JSON message"""

        last_fru_index = {}
        last_index = None
        for (index, date, event_time, device_id, device_type, sensor_num, event, status) \
                in self._get_sel_event():
            last_fru_index[device_type] = index
            last_index = index

        for (index, date, event_time, device_id, device_type, sensor_num, event, status) \
                in self._get_sel_event():

            is_last = (last_fru_index[device_type] == index)
            logger.debug(f"_notify_NodeDataMsgHandler '{device_type}': is_last: \
                                        {is_last}, sel_event: {(index, date, event_time, device_id, event, status)}")
            # TODO: Also use information from the command
            # 'ipmitool sel get <sel-entry-id>'
            # which gives more detailed information
            if device_type in self.fru_types:
                try:
                    self.fru_types[device_type](index, date, event_time, device_id,
                            sensor_num, event, status, is_last)
                except KeyError:
                    logger.warn(f"Sensor {sensor_num} for {device_type} is not present, ignoring event")
                except Exception as e:
                    logger.error(f"_notify_NodeDataMsgHandler, error {e} while processing \
                        sel_event: {(index, date, event_time, device_id, device_type, sensor_num, event, status)}, ignoring event")

        if last_index is not None:
            self._write_index_file(last_index)
        self.list_file.seek(0)
        self.list_file.truncate()

    def _run_command(self, command, out_file=subprocess.PIPE):
        """executes commands"""
        process = subprocess.Popen(command, shell=True, stdout=out_file, stderr=subprocess.PIPE)
        result = process.communicate()
        return result, process.returncode

    def _run_ipmitool_subcommand(self, subcommand, grep_args=None, out_file=subprocess.PIPE):
        """executes ipmitool sub-commands, and optionally greps the output"""

        res, err, retcode = \
            self.ipmi_client._run_ipmitool_subcommand(subcommand, grep_args)

        if self.IPMISIMTOOL in self.ipmi_client.ACTIVE_IPMI_TOOL:
            self.sdr_reset_required = True

        # check channel fault and fault resolved alert
        self._check_channel_error(err, retcode)

        # Detect if ipmitool removed or facing error after sensor initialized
        if retcode != 0:
            logger.error("%s can't fetch monitoring data for %s"
                         % (self.ipmi_client.NAME, self.SENSOR_NAME))
            if retcode == 1:
                if err.find(self.ipmi_client.VM_ERROR) != -1:
                    logger.error((f"{self.SENSOR_NAME}: {self.ipmi_client.NAME}"
                        f"error:: {err}\n Dependencies failed,"
                        "shutting down sensor"))
                    self.request_shutdown = True
                self.iem.iem_fault("IPMITOOL_ERROR")
                if self.IPMI not in self.iem.fault_iems:
                    self.iem.fault_iems.append(self.IPMI)
            elif retcode == BASH_ILLEGAL_CMD:
                logger.error(f"{self.SENSOR_NAME}: Required ipmitool missing \
                    on Node. Dependencies failed, shutting down sensor")
                self.request_shutdown = True
                self.iem.iem_fault("IPMITOOL_ERROR")
                if self.IPMI not in self.iem.fault_iems:
                    self.iem.fault_iems.append(self.IPMI)
        elif retcode == 0 and self.IPMI in self.iem.fault_iems:
            self.iem.iem_fault_resolved("IPMITOOL_AVAILABLE")
            self.iem.fault_iems.remove(self.IPMI)

        # write res to out_file only if there is no channel error
        if not self.channel_err and res:
            if out_file != subprocess.PIPE:
                out_file.write(res)

        return res, err, retcode

    def _check_channel_error(self, err, retcode):
        """Check BMC accessibility for active_interface."""
        logger.debug(f"Current active bmc interface is: {self.active_bmc_if}")
        if self.active_bmc_if == system:
            self.check_kcs_channel(err, retcode)
        elif self.active_bmc_if in BMCInterface.LAN_IF.value:
            self.check_lan_channel(err, retcode)
        # Set channel_err=True if both configured lan interface and fallback
        # KCS interface is inaccessible. OR Set it to True if configured
        # interface is system(KCS) and fault present for that interface.
        # and if channel_err=True node_hw resource monitoring will be stop.
        if all([self.system_fault, self.lan_fault]) == "fault" or \
            (self._channel_interface == system and self.system_fault == "fault"):
            self.channel_err = True
        # If any interface is accessible set channel_err=False
        # and if channel_err=False node_hw resource monitoring
        # will be resumed.
        elif any([self.system_fault, self.lan_fault]) != "fault":
            self.channel_err = False

    def check_kcs_channel(self, err, retcode):
        """Detect fault if err string contains possible cause/error listed in KCS_ERRS."""
        # If there is no prev fault raised for system interface and
        # 'err' contains possible error raise the fault alert for system
        # interface.
        if retcode != 0 and self.system_fault != "fault" and \
            (any(val in err for val in BMCInterface.KCS_ERRS.value)):
            self.get_channel_alert(INACTIVE_CHANNEL, system)
        if retcode == 0 and self.system_fault == "fault":
            self.get_channel_alert(ACTIVE_CHANNEL, system)

    def check_lan_channel(self, err, retcode):
        """Detect fault if err string contains possible cause/error listed in LAN_ERRS."""
        if retcode != 0 and self.lan_fault != "fault" and \
            (any(val in err for val in BMCInterface.LAN_ERRS.value)):
            self.get_channel_alert(INACTIVE_CHANNEL, self.active_bmc_if)
            # If error detected for lan/lanplus interface,
            # fallback to KCS interface.
            if self.active_bmc_if in BMCInterface.LAN_IF.value:
                logger.warning(
                    f"BMC is unreachable through {self.active_bmc_if}"
                    " interface, ipmitool fallback to KCS interface, if local"
                    " server is being monitored."
                    )
                self.active_bmc_if = system
                store.put(self.active_bmc_if, active_bmc_if_cache)

    def get_channel_alert(self, alert, IF_name):
        """create BMC interface alert json msg."""
        specific_info = {}
        alert_type = alert.alert
        severity = SeverityReader().map_severity(alert_type)
        channel_info = self.CHANNEL_INFO

        if IF_name in BMCInterface.LAN_IF.value:
            resource_type = "node:bmc:interface:rmcp"
            specific_info["bmc_user"] = self._bmc_user
            channel_info = self.LAN_CHANNEL_INFO
        else:
            resource_type = "node:bmc:interface:kcs"
            if alert_type == "fault":
                channel_info = self.KCS_CHANNEL_INFO
        info = {
                "resource_type": resource_type,
                "resource_id": channel_info["Channel Medium Type"],
                "event_time": str(int(time.time())),
                "description": alert.description.format(IF_name),
                "impact": alert.impact.format(IF_name),
                "recommendation": alert.recommendation.format(IF_name)
            }
        specific_info["channel info"] = channel_info
        # Update cache
        data = ""
        key = ""
        if IF_name == system:
            self.system_fault = alert_type
            data = self.system_fault
            key = system_cache_path
        elif IF_name in BMCInterface.LAN_IF.value:
            self.lan_fault = alert_type
            data = self.lan_fault
            key = lan_cache_path

        store.put(data, key)
        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)

    def read_data(self):
        return self.sel_event_info

    def _get_sensor_list_by_type(self, sensor_type):
        """get list of sensors of type 'sensor_type'
           Returns a list of tuples, of which
           the first element is the sensor id and
           the second is the number."""

        sensor_list_out, err, retcode = \
            self._run_ipmitool_subcommand(f"sdr type '{sensor_type}'")
        out = []

        if retcode != 0:
            msg = f"ipmitool sdr type command failed: {err}"
            logger.warning(msg)
            return out

        sensor_list = sensor_list_out.split("\n")

        for sensor in sensor_list:
            if self.IPMI_SDR_ERR in sensor:
                self.sdr_reset_required = True
                return out
            if sensor == "":
                break
            # Example of output form 'sdr type' command:
            # Sys Fan 2B       | 33h | ok  | 29.4 | 5332 RPM
            # PS1 1a Fan Fail  | A0h | ok  | 29.13 |
            # HDD 1 Status     | F1h | ok  |  4.2 | Drive Present
            fields_list = [ f.strip() for f in sensor.split("|")]
            sensor_id, sensor_num, status, entity_id, reading  = fields_list
            sensor_num = sensor_num.strip("h").lower()

            out.append((sensor_id, sensor_num))
        return out

    def _get_sensor_list_by_entity(self, entity_id):
        """get list of sensors belonging to entity 'entity_id'
           Returns a list of sensor IDs"""

        sensor_list_out, err, retcode = \
            self._run_ipmitool_subcommand(f"sdr entity '{entity_id}'")
        if retcode != 0:
            msg = f"ipmitool sdr entity command failed: {err}"
            logger.error(msg)
            return
        sensor_list = sensor_list_out.split("\n")

        out = []
        for sensor in sensor_list:
            if self.IPMI_SDR_ERR in sensor:
                return out
            if sensor == '':
                continue
            # Output from 'sdr entity' command is same as from 'sdr type' command.
            fields_list = [f.strip() for f in sensor.split("|")]
            sensor_id, sensor_num, status, entity_id, reading = fields_list
            sensor_num = sensor_num.strip("h").lower()

            out.append(sensor_id)
        return out

    def _get_sensor_sdr_props(self, sensor_id):
        props_list_out, err, retcode = \
            self._run_ipmitool_subcommand(f"sdr get '{sensor_id}'")
        if retcode != 0:
            msg = f"ipmitool sensor get command failed: {err}"
            logger.warning(msg)
            return
        props_list = props_list_out.split("\n")

        static_keys = {}
        dynamic = {}
        curr_key = None
        for prop in props_list:
            if self.IPMI_SDR_ERR in prop:
                return (dynamic, static_keys)
            if prop == '':
                continue
            if ':' in prop and '[' not in prop and ']' not in prop:
                curr_key, val = [f.strip() for f in prop.split(":")]
                static_keys[curr_key] = val
            else:
                static_keys[curr_key] += "\n" + prop

        common_props = {
            'Sensor ID',
            'Entity ID',
        }
        # Whatever keys from DYNAMIC_KEYS are present,
        # move them to the 'dynamic' dict
        for c in (set(static_keys.keys()) & self.DYNAMIC_KEYS):
            dynamic[c] = static_keys[c]
            del static_keys[c]

        return (dynamic, static_keys)

    def _get_sensor_props(self, sensor_id):
        """get all the properties of a sensor.
           Returns a tuple (common, specific) where
           common is a dict of common sensor properties and
           their values for this sensor, and
           specific is a dict of the properties specific to this sensor"""
        props_list_out, err, retcode = \
            self._run_ipmitool_subcommand(f"sensor get '{sensor_id}'")
        if retcode != 0:
            msg = f"ipmitool sensor get command failed: {err}"
            logger.warning(msg)
            return (False, False, False)
        props_list = props_list_out.split('\n')
        props_list = props_list[1:] # The first line is 'Locating sensor record...'

        specific_static = {}
        common = {}
        specific_dynamic = {}
        curr_key = None
        for prop in props_list:
            if self.IPMI_SDR_ERR in prop:
                return (common, specific_static, specific_dynamic)
            if prop == '':
                continue
            if ':' in prop:
                curr_key, val = [f.strip() for f in prop.split(":")]
                specific_static[curr_key] = val
            else:
                specific_static[curr_key] += "\n" + prop

        common_props = {
            'Sensor ID',
            'Entity ID',
        }
        # Whatever keys from common_props are present,
        # move them to the 'common' dict
        for c in (set(specific_static.keys()) & common_props):
            common[c] = specific_static[c]
            del specific_static[c]

        for c in (set(specific_static.keys()) & self.DYNAMIC_KEYS):
            specific_dynamic[c] = specific_static[c]
            del specific_static[c]

        return (common, specific_static, specific_dynamic)

    def _parse_fan_info(self, index, date, _time, device_id, sensor_id,\
                                                 event, status, is_last):
        """Parse out Fan realted changes that gets reaflected in the ipmi sel list"""

        #TODO: Can enrich the sspl event message with more FRU info using
        # command 'ipmitool sel get <sel-id>'

        fan_info = {}
        alert_type = None

        #TODO: Enabled Assertions list (fan_specific_list[] in code) needs
        # to be built dynamically to support platform specific assertions and
        # not limit to these hardcoded ones.
        fan_specific_list = ["Sensor Reading", "Lower Non-Recoverable",
                             "Upper Non-Recoverable","Upper Non-Critical",
                             "Lower Critical", "Lower Non-Critical",
                             "Upper Critical", "Fully Redundant", "State Asserted",
                             "State Deasserted"]

        # Strip spaces just to be sure
        event = event.strip()
        status = status.strip()

        # Ensure that event and status are unchanged for next use.
        original_event = event
        original_status = status

        if status.lower() == "deasserted" and event.lower() == "fully redundant":
            alert_type = "fault"
        elif status.lower() == "asserted" and event.lower() == "fully redundant":
            alert_type = "fault_resolved"
        elif "going high" in event.lower() or "going low" in event.lower():
            if status.lower() == "deasserted":
                alert_type = "fault_resolved"
                event = "Deasserted - " + event
            elif status.lower() == "asserted":
                alert_type = "fault"
                event = "Asserted - " + event

        sensor_name = self.sensor_id_map[self.TYPE_FAN][sensor_id]

        fan_common_data, fan_specific_data, fan_specific_data_dynamic = self._get_sensor_props(sensor_name)

        for key in list(fan_specific_data):
            if key not in fan_specific_list:
                del fan_specific_data[key]

        fan_info = fan_specific_data
        fan_info.update({"fru_id" : device_id, "event" : event})
        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_FAN
        fru = self.ipmi_client.is_fru(self.fru_map[self.TYPE_FAN])
        severity_reader = SeverityReader()
        if alert_type:
            severity = severity_reader.map_severity(alert_type)
        else:
            # Else section will handle some unknown as well as known events like
            # "State Asserted", "State Deasserted" or "Sensor Reading" and also it is
            # keeping default severity and alert_type for those events.
            alert_type = "miscellaneous"
            severity = "informational"

        fru_info = {    "resource_type": resource_type,
                        "fru": fru,
                        "resource_id": sensor_name,
                        "event_time": self._get_epoch_time_from_date_and_time(date, _time),
                        "description": event
                    }

        if is_last:
            fan_info.update(fan_specific_data_dynamic)

        if alert_type == "fault":
            self.faulty_resources[sensor_name] = {
                'status': original_status,
                'event': original_event,
                'device_id': device_id,
                'fru_type': self.TYPE_FAN
            }
        elif alert_type in ['fault_resolved', 'miscellaneous'] and sensor_name in self.faulty_resources:
            del self.faulty_resources[sensor_name]

        self._send_json_msg(resource_type, alert_type, severity, fru_info, fan_info)
        store.put(self.faulty_resources, self.faulty_resources_path)

    def _parse_psu_supply_info(self, index, date, _time, sensor, sensor_num, event, status, is_last):
        """Parse out PSU related changes that gets reflected in the ipmi sel list"""

        alerts = {
            ("Config Error", "Asserted"): ("fault","error"),
            ("Config Error", "Deasserted"): ("fault_resolved","informational"),
            ("Failure detected ()", "Asserted"): ("fault","error"),
            ("Failure detected ()", "Deasserted"): ("fault_resolved","informational"),
            ("Failure detected", "Asserted"): ("fault","error"),
            ("Failure detected", "Deasserted"): ("fault_resolved","informational"),
            ("Power Supply AC lost", "Asserted"): ("fault","critical"),
            ("Power Supply AC lost", "Deasserted"): ("fault_resolved","informational"),
            ("Power Supply Inactive", "Asserted"): ("fault","critical"),
            ("Power Supply Inactive", "Deasserted"): ("fault_resolved","informational"),
            ("Predictive failure", "Asserted"): ("fault","warning"),
            ("Predictive failure", "Deasserted"): ("fault_resolved","informational"),
            ("Predictive failure ()", "Asserted"): ("fault","warning"),
            ("Predictive failure ()", "Deasserted"): ("fault_resolved","informational"),
            ("Presence detected", "Asserted"): ("insertion","informational"),
            ("Presence detected", "Deasserted"): ("missing","critical"),
            ("Presence detected ()", "Asserted"): ("insertion","informational"),
            ("Presence detected ()", "Deasserted"): ("missing","critical"),
        }

        sensor_id = self.sensor_id_map[self.TYPE_PSU_SUPPLY][sensor_num]
        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_PSU
        fru = self.ipmi_client.is_fru(self.fru_map[self.TYPE_PSU_SUPPLY])
        info = {
            "resource_type": resource_type,
            "fru": fru,
            "resource_id": sensor,
            "event_time": self._get_epoch_time_from_date_and_time(date, _time),
            "description": event
        }

        try:
            (alert_type, severity) = alerts[(event, status)]
        except KeyError:
            logger.error(f"Unknown event: {event}, status: {status}")
            return

        dynamic, static = self._get_sensor_sdr_props(sensor_id)
        specific_info = {}
        specific_info["fru_id"] = sensor

        specific_info.update(static)

        # Remove unnecessary characters props
        for key in ['Deassertions Enabled', 'Assertions Enabled',
                    'States Asserted', 'Assertion Events']:
            try:
                specific_info[key] = re.sub(',  +', ', ', re.sub('[\[\]]','', \
                    specific_info[key]).replace('\n',','))
            except KeyError:
                pass

        if is_last:
            specific_info.update(dynamic)

        if alert_type in ["fault", "missing"]:
            self.faulty_resources[sensor_id] = {
                'status': status,
                'event': event,
                'device_id': sensor,
                'fru_type': self.TYPE_PSU_SUPPLY
            }
        elif alert_type in ['fault_resolved', 'miscellaneous', 'insertion'] and \
            sensor_id in self.faulty_resources:
            del self.faulty_resources[sensor_id]

        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
        store.put(self.faulty_resources, self.faulty_resources_path)

    def _parse_psu_unit_info(self, index, date, _time, sensor, sensor_num, event, status, is_last):
        """Parse out PSU related changes that gets reflected in the ipmi sel list"""

        alerts = {

            ("240VA power down", "Asserted"): ("fault", "critical"),
            ("240VV power down", "Deasserted"): ("fault_resolved", "informational"),
            ("AC lost", "Asserted"): ("fault", "critical"),
            ("AC lost", "Deasserted"): ("fault_resolved", "informational"),
            ("Failure detected", "Asserted"): ("fault", "critical"),
            ("Failure detected", "Deasserted"): ("fault_resolved", "informational"),
            ("Failure detected ()", "Asserted"): ("fault", "critical"),
            ("Failure detected ()", "Deasserted"): ("fault_resolved", "informational"),
            ("Power off/down", "Asserted"): ("fault", "critical"),
            ("Power off/down", "Deasserted"): ("fault_resolved", "informational"),
            ("Soft-power control failure", "Asserted"): ("fault", "warning"),
            ("Soft-power control failure", "Deasserted"): ("fault_resolved", "informational"),
            ("Fully Redundant", "Asserted"): ("fault_resolved", "informational"),
            ("Fully Redundant", "Deasserted"): ("fault", "warning"),
            ("Non-Redundant: Insufficient Resources", "Asserted"): ("fault", "critical"),
            ("Non-Redundant: Insufficient Resources", "Deasserted"): ("fault_resolved", "informational"),
            ("Non-Redundant: Sufficient from Insufficient", "Asserted"): ("fault", "warning"),
            ("Non-Redundant: Sufficient from Insufficient", "Deasserted"): ("fault", "warning"),
            ("Non-Redundant: Sufficient from Redundant", "Asserted"): ("fault", "warning"),
            ("Non-Redundant: Sufficient from Redundant", "Deasserted"): ("fault", "informational"),
            ("Redundancy Degraded", "Asserted"): ("fault", "warning"),
            ("Redundancy Degraded", "Deasserted"): ("fault_resolved", "informational"),
            ("Redundancy Degraded from Fully Redundant", "Asserted"): ("fault", "warning"),
            ("Redundancy Degraded from Fully Redundant", "Deasserted"): ("fault_resolved", "warning"),
            ("Redundancy Degraded from Non-Redundant", "Asserted"): ("fault", "critical"),
            ("Redundancy Degraded from Non-Redundant", "Deasserted"): ("fault_resolved", "warning"),
            ("Redundancy Lost", "Asserted"): ("fault", "warning"),
            ("Redundancy Lost", "Deasserted"): ("fault_resolved", "informational"),

        }

        sensor_id = self.sensor_id_map[self.TYPE_PSU_UNIT][sensor_num]
        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_PSU
        fru = self.ipmi_client.is_fru(self.fru_map[self.TYPE_PSU_UNIT])
        info = {
            "resource_type": resource_type,
            "fru": fru,
            "resource_id": sensor,
            "event_time": self._get_epoch_time_from_date_and_time(date, _time),
            "description": event
        }

        try:
            (alert_type, severity) = alerts[(event, status)]
        except KeyError:
            logger.error(f"Unknown event: {event}, status: {status}")
            return

        dynamic, static = self._get_sensor_sdr_props(sensor_id)
        specific_info = {}
        specific_info["fru_id"] = sensor

        specific_info.update(static)

        for key in ['Deassertions Enabled', 'Assertions Enabled',
                    'Assertion Events', 'States Asserted']:
            try:
                specific_info[key] = re.sub(',  +', ', ', re.sub('[\[\]]','', \
                    specific_info[key]).replace('\n',','))
            except KeyError:
                pass

        if is_last:
            specific_info.update(dynamic)

        if alert_type == "fault":
            self.faulty_resources[sensor_id] = {
                'status': status,
                'event': event,
                'device_id': sensor,
                'fru_type': self.TYPE_PSU_UNIT
            }
        elif alert_type in ['fault_resolved', 'miscellaneous'] and sensor_id in self.faulty_resources:
            del self.faulty_resources[sensor_id]

        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
        store.put(self.faulty_resources, self.faulty_resources_path)

    def get_index_from_sensor_id_map(self, hw_type, sensor_num):
        """Assign and return sensor index to sensors of given hw_type.

           Usecase:
            sensor_id_map = {
                "Power Supply": {
                    'f1': 'PS Redundancy',
                    'f2': 'Status',
                    'f3': 'Status'
                    }
                }
            In such case where sensor_id's are not unique or does not
            have a numerical identifier, assign numerical sensor id
            starting with 0.
            indices are assigned according to sorted hexadecimal
            sensor number.
        """
        return sorted(list(
            self.sensor_id_map[hw_type].keys())).index(sensor_num)

    def _parse_disk_info(self, index, date, _time, sensor, sensor_num, event, status, is_last):
        """Parse out Disk related changes that gets reaflected in the ipmi sel list"""

        sensor_id = self.sensor_id_map[self.TYPE_DISK][sensor_num]
        disk_slot = re.search(r'\d+', sensor_id)
        if disk_slot:
            disk_slot = disk_slot.group()
        else:
            disk_slot = self.get_index_from_sensor_id_map(self.TYPE_DISK,
                                                          sensor_num)
        if 'Status' in sensor_id:
            disk_name = sensor_id.replace('Status', f'(0x{sensor_num})')
        else:
            disk_name = sensor_id +  f' (0x{sensor_num})'

        common, specific, specific_dynamic = self._get_sensor_props(sensor_id)
        if common:
            if not specific:
                specific = {"States Asserted": "N/A", "Sensor Type (Discrete)": "N/A"}
            specific_info = specific
            resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_DISK
            try:
                alert = alert_for_event[self.TYPE_DISK][event][status]
            except KeyError:
                logger.error(f"{self.TYPE_DISK} : " +
                             f"Unknown event: {event}, status: {status}")
                return
            except Exception as e:
                logger.exception(e)
                return
            info = {
                "resource_type": resource_type,
                "fru": self.ipmi_client.is_fru(self.fru_map[self.TYPE_DISK]),
                "resource_id": disk_name,
                "event_time": self._get_epoch_time_from_date_and_time(date, _time),
                "description": alert.description.format(disk_slot, disk_name),
                "impact": alert.impact,
                "recommendation": alert.recommendation
            }
            specific_info["fru_id"] = disk_name

            if is_last:
                specific_info.update(specific_dynamic)

            for key in ['Deassertions Enabled', 'Assertions Enabled',
                        'Assertion Events', 'States Asserted']:
                try:
                    specific_info[key] = re.sub(',  +', ', ', re.sub('[\[\]]','', \
                        specific_info[key]).replace('\n',','))
                except KeyError:
                    pass

            if alert.type in ["fault", "missing"]:
                self.faulty_resources[sensor_id] = {
                    'status': status,
                    'event': event,
                    'device_id': sensor,
                    'fru_type': self.TYPE_DISK
                }
            elif alert.type in ['fault_resolved', 'insertion'] and \
                sensor_id in self.faulty_resources:
                del self.faulty_resources[sensor_id]

            self._send_json_msg(resource_type, alert.type, alert.severity,
                                info, specific_info)
            store.put(self.faulty_resources, self.faulty_resources_path)

    def _parse_temperature_info(self, index, date, _time, sensor, sensor_num, event, status, is_last):

        sensor_name = self.sensor_id_map[self.TYPE_TEMPERATURE][sensor_num]
        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_TEMPERATURE

        threshold = event.split(" ")[-1]
        if threshold.lower() in ['low', 'high']:
            alert_type = f"threshold_breached:{threshold}"
        if alert_type:
            severity_reader = SeverityReader()
            severity = severity_reader.map_severity(alert_type)
            if threshold.lower() in ['low', 'high'] and status.lower() == "deasserted":
                severity = "informational"
        else:
            alert_type = "miscellaneous"
            severity = "informational"


        common, specific, specific_dynamic = self._get_sensor_props(sensor_name)

        specific_info = {}
        specific_info.update(common)
        specific_info.update(specific)
        specific_info.update({'fru_id': sensor})
        if is_last:
            specific_info.update(specific_dynamic)

        info = {
            "resource_type": resource_type,
            "resource_id": sensor_name,
            "event_time": self._get_epoch_time_from_date_and_time(date, _time),
            "description": event
        }

        if (threshold.lower() in ['low', 'high'] and status.lower() == "asserted"):
            self.faulty_resources[sensor_name] = {
                'status': status,
                'event': event,
                'device_id': sensor,
                'fru_type': self.TYPE_TEMPERATURE
            }
        elif (alert_type in ['fault_resolved', 'miscellaneous'] or \
            (threshold.lower() in ['low', 'high'] and status.lower() == "deasserted")) \
                and sensor_name in self.faulty_resources:
            del self.faulty_resources[sensor_name]

        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
        store.put(self.faulty_resources, self.faulty_resources_path)

    def _parse_voltage_info(self, index, date, _time, sensor, sensor_num, event, status, is_last):

        sensor_name = self.sensor_id_map[self.TYPE_VOLTAGE][sensor_num]
        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_VOLTAGE

        threshold = event.split(" ")[-1]
        if threshold.lower() in ['low', 'high']:
            alert_type = f"threshold_breached:{threshold}"
        if alert_type:
            severity_reader = SeverityReader()
            severity = severity_reader.map_severity(alert_type)
            if threshold.lower() in ['low', 'high'] and status.lower() == "deasserted":
                severity = "informational"
        else:
            alert_type = "miscellaneous"
            severity = "informational"


        common, specific, specific_dynamic = self._get_sensor_props(sensor_name)

        specific_info = {}
        specific_info.update(common)
        specific_info.update(specific)
        specific_info.update({'fru_id': sensor})
        if is_last:
            specific_info.update(specific_dynamic)

        info = {
            "resource_type": resource_type,
            "resource_id": sensor_name,
            "event_time": self._get_epoch_time_from_date_and_time(date, _time),
            "description": event
        }

        if (threshold.lower() in ['low', 'high'] and status.lower() == "asserted"):
            self.faulty_resources[sensor_name] = {
                'status': status,
                'event': event,
                'device_id': sensor,
                'fru_type': self.TYPE_VOLTAGE
            }
        elif (alert_type in ['fault_resolved', 'miscellaneous'] or \
            (threshold.lower() in ['low', 'high'] and status.lower() == "deasserted")) \
                and sensor_name in self.faulty_resources:
            del self.faulty_resources[sensor_name]

        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
        store.put(self.faulty_resources, self.faulty_resources_path)

    def _parse_current_info(self, index, date, _time, sensor, sensor_num, event, status, is_last):
        """Parse out 'current' related changes that gets reflected in the ipmi sel list."""
        sensor_name = self.sensor_id_map[self.TYPE_CURRENT][sensor_num]
        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_CURRENT
        threshold = event.split(" ")[-1]
        if threshold.lower() in ['low', 'high']:
            alert_type = f"threshold_breached:{threshold}"
        if alert_type:
            severity_reader = SeverityReader()
            severity = severity_reader.map_severity(alert_type)
            if (
                threshold.lower() in ['low', 'high'] and
                    status.lower() == "deasserted"):
                severity = "informational"
        else:
            alert_type = "miscellaneous"
            severity = "informational"
        common, specific, specific_dynamic = self._get_sensor_props(sensor_name)

        specific_info = {}
        specific_info.update(common)
        specific_info.update(specific)
        specific_info.update({'fru_id': sensor})
        if is_last:
            specific_info.update(specific_dynamic)

        info = {
            "resource_type": resource_type,
            "resource_id": sensor_name,
            "event_time": self._get_epoch_time_from_date_and_time(date, _time),
            "description": event
        }

        if (threshold.lower() in ['low', 'high'] and status.lower() == "asserted"):
            self.faulty_resources[sensor_name] = {
                'status': status,
                'event': event,
                'device_id': sensor,
                'fru_type': self.TYPE_CURRENT
            }
        elif (alert_type in ['fault_resolved', 'miscellaneous'] or
                (threshold.lower() in ['low', 'high'] and
                    status.lower() == "deasserted")) \
                and sensor_name in self.faulty_resources:
            del self.faulty_resources[sensor_name]

        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
        store.put(self.faulty_resources, self.faulty_resources_path)

    def _send_json_msg(self, resource_type, alert_type, severity, info, specific_info):
        """Transmit data to NodeDataMsgHandler which takes two arguments.
           device will be device name and data will consist of relevant data"""

        internal_json_msg = json.dumps({
            "sensor_request_type" : {
                "node_data":{
                    "alert_type": alert_type,
                    "severity": severity,
                    "alert_id": self._get_alert_id(info["event_time"]),
                    "host_id": self.host_id,
                    "info": info,
                    "specific_info": specific_info
                }
            }
          })

        # Send the event to node data message handler to generate json message and send out
        self._write_internal_msgQ(NodeDataMsgHandler.name(), internal_json_msg)

    def _get_alert_id(self, epoch_time):
        """Returns alert id which is a combination of
           epoch_time and salt value
        """
        salt = str(uuid.uuid4().hex)
        alert_id = epoch_time + salt
        return alert_id

    def _get_epoch_time_from_date_and_time(self, _date, _time):
        timestamp_format = '%m/%d/%Y %H:%M:%S'
        timestamp = time.strptime('{} {}'.format(_date,_time), timestamp_format)
        return str(int(calendar.timegm(timestamp)))

    def suspend(self):
        """Suspends the module thread. It should be non-blocking"""
        super(NodeHWsensor, self).suspend()
        self._suspended = True

    def resume(self):
        """Resumes the module thread. It should be non-blocking"""
        super(NodeHWsensor, self).resume()
        self._suspended = False

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(NodeHWsensor, self).shutdown()
