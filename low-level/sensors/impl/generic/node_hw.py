"""
 ****************************************************************************
 Filename:          node_hw.py
 Description:       Fetches Server FRUs and Logical Sensor data using inband IPMI interface to BMC
 Creation Date:     11/04/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2019/04/11 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import subprocess
import time
import json
import re
import socket
import uuid

from zope.interface import implementer

from framework.utils.severity_reader import SeverityReader
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from message_handlers.logging_msg_handler import LoggingMsgHandler

from framework.base.debug import Debug
from framework.base.module_thread import SensorThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.base.sspl_constants import PRODUCT_FAMILY
from framework.base.sspl_constants import COMMON_CONFIGS,ServiceTypes
from framework.utils.config_reader import ConfigReader
from framework.utils.service_logging import logger
from framework.utils import encryptor
from sensors.INode_hw import INodeHWsensor

# bash exit codes
BASH_ILLEGAL_CMD = 127

@implementer(INodeHWsensor)
class NodeHWsensor(SensorThread, InternalMsgQ):
    """Obtains data about the FRUs and logical sensors and updates
       if any state change occurs"""


    SENSOR_NAME = "NodeHWsensor"
    PRIORITY = 1

    SYSINFO = "SYSTEM_INFORMATION"
    DATA_PATH_KEY = "data_path"
    DATA_PATH_VALUE_DEFAULT = f"/var/{PRODUCT_FAMILY}/sspl/data"

    sel_event_info = ""

    TYPE_PSU_SUPPLY = 'Power Supply'
    TYPE_PSU_UNIT = 'Power Unit'
    TYPE_FAN = 'Fan'
    TYPE_DISK = 'Drive Slot / Bay'

    SEL_USAGE_THRESHOLD = 90
    SEL_INFO_PERC_USED = "Percent Used"
    SEL_INFO_FREESPACE = "Free Space"
    SEL_INFO_ENTRIES = "Entries"

    CACHE_DIR_NAME  = "server"
    # This file stores the last index from the SEL list for which we have issued an event.
    INDEX_FILE = "last_sel_index"
    LIST_FILE  = "sel_list"
    LIST_FILE_COLLECT = "sel_list_collect"

    UPDATE_CREATE_MODE = "w+"
    UPDATE_ONLY_MODE   = "r+"

    IPMI_ERRSTR = "Could not open device at "
    IPMI_SDR_ERR = "command failed"
    IPMI_ENCODING = 'utf-8'

    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    SITE_ID = "site_id"
    RACK_ID = "rack_id"
    NODE_ID = "node_id"
    CLUSTER_ID = "cluster_id"

    BMC_INTERFACE = "BMC_INTERFACE"
    BMC_LAN_USER = "user"
    BMC_LAN_PASSWD = "secret"
    BMC_LAN_IP = "ip"
    BMC_CHANNEL_IF = "default"

    SYSTEM_IF = "system"
    LAN_IF = "lan"

    RMCP_ERRS = ("Unable to establish LAN session", "Unable to establish IPMI v1.5 / RMCP session",
                "Unable to establish IPMI v2 / RMCP+ session" ,"connection timeout","session timeout",
                "driver timeout","message timeout","Address lookup for -U failed","BMC busy","invalid user name",
                "password invalid","password verification timeout","k_g invalid","privilege level insufficient",
                "privilege level cannot be obtained for this user","authentication type unavailable for attempted privilege level" )

    KCS_ERRS = ("could not find inband device", "driver timeout")
    CHANNEL_INFO = {}

    channel_err = False
    kcs_interface_alert = False
    lan_interface_alert = False

    sdr_reset_required = False
    request_shutdown = False
    sel_last_queried = None
    SEL_QUERY_FREQ = 300

    NODEHWSENSOR = "NODEHWSENSOR"
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
                    "plugins": ["NodeDataMsgHandler", "LoggingMsgHandler"],
                    "rpms": []
    }

    @staticmethod
    def name():
        """@return: name of the module."""
        return NodeHWsensor.SENSOR_NAME

    def __init__(self):
        super(NodeHWsensor, self).__init__(self.SENSOR_NAME.upper(), self.PRIORITY)
        self.host_id = self._get_host_id()

        self.fru_types = {
            self.TYPE_FAN: self._parse_fan_info,
            self.TYPE_PSU_SUPPLY: self._parse_psu_supply_info,
            self.TYPE_PSU_UNIT: self._parse_psu_unit_info,
            self.TYPE_DISK: self._parse_disk_info,
        }

        # Flag to indicate suspension of module
        self._suspended = False

        # Validate configuration file for required valid values
        try:
            self.conf_reader = ConfigReader()
            self.file_conf_reader = ConfigReader(is_test=True, test_config_path='/etc/sspl.conf')

        except (IOError, ConfigReader.Error) as err:
            logger.error("[ Error ] when validating the config file {0} - {1}"\
                 .format(self.CONF_FILE, err))
        self.polling_interval = int(self.conf_reader._get_value_with_default(
            self.NODEHWSENSOR, self.POLLING_INTERVAL, self.DEFAULT_POLLING_INTERVAL))

    def _get_file(self, name):
        if os.path.exists(name):
            mode = self.UPDATE_ONLY_MODE
        else:
            mode = self.UPDATE_CREATE_MODE
        return open(name, mode)

    def _initialize_cache(self):
        data_dir =  self.conf_reader._get_value_with_default(
            self.SYSINFO, COMMON_CONFIGS.get(self.SYSINFO).get(self.DATA_PATH_KEY), self.DATA_PATH_VALUE_DEFAULT)
        self.cache_dir_path = os.path.join(data_dir, self.CACHE_DIR_NAME)

        if not os.path.exists(self.cache_dir_path):
            logger.info(f"Creating cache dir: {self.cache_dir_path}")
            os.makedirs(self.cache_dir_path)
        logger.info(f"Using cache dir: {self.cache_dir_path}")

        self.index_file_name = os.path.join(self.cache_dir_path, self.INDEX_FILE)

        bad_index_file = \
                not os.path.exists(self.index_file_name) or \
                os.path.getsize(self.index_file_name) == 0
        if bad_index_file:
            self._write_index_file(0)
        # Now self.index_file has a valid sel index in it

        self.list_file_name = os.path.join(self.cache_dir_path, self.LIST_FILE)
        self.list_file = self._get_file(self.list_file_name)

        self.list_file_collect_name = os.path.join(self.cache_dir_path, self.LIST_FILE_COLLECT)

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

        self._site_id = conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.SITE_ID),
                                                '001')
        self._rack_id = conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.RACK_ID),
                                                '001')
        self._node_id = conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.NODE_ID),
                                                '001')
        self._cluster_id = conf_reader._get_value_with_default(
                                                self.SYSTEM_INFORMATION,
                                                COMMON_CONFIGS.get(self.SYSTEM_INFORMATION).get(self.CLUSTER_ID),
                                                '001')
        self._bmc_user = conf_reader._get_value_with_default(
                                                self.BMC_INTERFACE,
                                                self.BMC_LAN_USER,
                                                'ADMIN')
        self._bmc_passwd = conf_reader._get_value_with_default(
                                                self.BMC_INTERFACE,
                                                self.BMC_LAN_PASSWD,
                                                'ADMIN')
        self._bmc_ip = conf_reader._get_value_with_default(
                                                self.BMC_INTERFACE,
                                                self.BMC_LAN_IP,
                                                '')
        self._channel_interface = self.file_conf_reader._get_value_with_default(
                                                self.BMC_INTERFACE,
                                                self.BMC_CHANNEL_IF,
                                                'system')

        decryption_key = encryptor.gen_key(self._cluster_id, ServiceTypes.CLUSTER.value)
        self._bmc_passwd = encryptor.decrypt(decryption_key, self._bmc_passwd.encode('ascii'), 'Node_hw')

        # Set flag 'request_shutdown' to true if ipmitool/simulator is non-functional
        res, retcode = self._run_ipmitool_subcommand("sel info")
        if retcode != 0 and self.channel_err is False:
                self.request_shutdown = True
        else:
            self._initialize_cache()
            self._fetch_channel_info()
            if self.channel_err is False:
                self._read_sensor_list()

        return True

    def _fetch_channel_info(self):
        # fetch bmc interface (KCS or LAN)  information
        res, retcode = self._run_ipmitool_subcommand("channel info")
        if retcode == 0:
            resstr = b''.join([val for val in res if val]).decode(self.IPMI_ENCODING)
            channel_info = resstr.strip().split("\n")
            # convert channel_info into dict
            channel_info = {k.strip():v.strip() for k,v in (x.split(":") for x in channel_info[1:]\
                            if ":" in x)}
            self.CHANNEL_INFO = channel_info

    def _update_list_file(self):
        with open(self.list_file_collect_name, self.UPDATE_CREATE_MODE) as f:
            # make sel list filter only for available frus. no extra data needed
            # 'Power Supply|Power Unit|Fan|Drive Slot / Bay'
            f.seek(0)
            f.truncate()
            available_fru = '|'.join(self.fru_types.keys())
            sel_out, retcode = self._run_ipmitool_subcommand(
                    "sel list", grep_args=f"{available_fru}",
                    out_file=f)
            if retcode != 0:
                if isinstance(sel_out, tuple):
                    sel_out = [val for val in sel_out if val]
                msg = f"ipmitool sel list command failed: {b''.join(sel_out)}"
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
            sel_info, retcode = self._run_ipmitool_subcommand("sel info")
            if retcode != 0:
                logger.error(f"ipmitool sel info command failed,  \
                    with err {sel_info}")
                return (False)

            # record SEL last queried time
            self.sel_last_queried = time.time()

            key = val = None
            info_list = b''.join(sel_info).decode(self.IPMI_ENCODING).split("\n")

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

                cleared, retcode = self._run_ipmitool_subcommand("sel clear")
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
                if self.channel_err:
                    self._fetch_channel_info()

                # Reset sensor_map_id after ipmi simulation
                if not os.path.exists("/tmp/activate_ipmisimtool"):
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

                self._check_and_clear_sel()
            except Exception as ae:
                logger.exception(ae)

            # Reset debug mode if persistence is not enabled
            self._disable_debug_if_persist_false()
            self._scheduler.enter(self.polling_interval, self._priority, self.run, ())
        else:
            logger.warning(f"{self.SENSOR_NAME} Node hw monitoring disabled")
            self.shutdown()

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
            try:
                device_type, sensor_num = re.match(
                        '(.*) (#0x([0-9a-f]+))?', device_id).group(1, 3)
            except:
                # If device_type and sensor_num is not found in device_id
                device_type = device_id
                sensor_num = ''

            return (index, date, _time, device_id, device_type, sensor_num, event, status)

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
                self.fru_types[device_type](index, date, event_time, device_id,
                        sensor_num, event, status, is_last)

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

        ipmi_tool = self.IPMITOOL

        # A dummy file path check to select ipmi simulator if
        # simulator is required, otherwise default ipmitool.
        if os.path.exists("/tmp/activate_ipmisimtool"):
            res, retcode = self._run_command(command=f"{self.IPMISIMTOOL} sel info")
            if retcode == 0:
                ipmi_tool = self.IPMISIMTOOL
                logger.debug("IPMI simulator is activated")
                self.sdr_reset_required = True

        if self._channel_interface == self.SYSTEM_IF or ipmi_tool == self.IPMISIMTOOL:
            command = ipmi_tool + subcommand
        elif self._channel_interface == self.LAN_IF and ipmi_tool != self.IPMISIMTOOL:
            command = ipmi_tool + " -H " + self._bmc_ip + " -U " + self._bmc_user + \
                        " -P " + self._bmc_passwd + " -I " + "lan " + subcommand

        res, retcode = self._run_command(command, subprocess.PIPE)

        # check channel fault and fault resolved alert
        self._check_channel_error(res,retcode)

        # Detect if ipmitool removed or facing error after sensor initialized
        if retcode != 0:
            logger.error(f"{ipmi_tool} can't fetch monitoring data for {self.SENSOR_NAME}")
            if retcode == 1:
                if isinstance(res, tuple):
                    resstr = b''.join([val for val in res if val])
                    resstr = resstr.decode(self.IPMI_ENCODING)
                    if resstr.find(self.IPMI_ERRSTR) == 0:
                        logger.error(f"{self.SENSOR_NAME}: {ipmi_tool} error:: {resstr}\n \
                            Dependencies failed, shutting down sensor")
                        self.request_shutdown = True
            elif (retcode == BASH_ILLEGAL_CMD):
                logger.error(f"{self.SENSOR_NAME}: Required ipmitool missing on Node. Dependencies failed, shutting down sensor")
                self.request_shutdown = True

        if grep_args is not None and retcode == 0 and isinstance(res, tuple):
            import re
            final_list = []
            for l in res[0].decode(encoding=self.IPMI_ENCODING).split('\n'):
                if re.search(grep_args, l) is not None:
                    final_list += [l]
            res = ('\n'.join(final_list), res[1])
        if out_file != subprocess.PIPE:
            out_file.write(res[0])

        return res, retcode

    def _check_channel_error(self, res, retcode):
        # check res present in possible errors or not

        resource_id = None
        resource_type = None
        alert_type = None
        channel_info = {}
        channel_status = None
        epoch_time = str(int(time.time()))

        res = b''.join([val for val in res if val]).decode(self.IPMI_ENCODING)
        if retcode != 0:
            err_index = res.find("Error")
            if err_index >= 0:
                err = res[err_index:].split("Error:")[1].strip()
            else:
                err = res.split("\n")[0]
        else:
            err = res

        if self._channel_interface == self.SYSTEM_IF:
            kcs_channel_info = self._check_kcs_if_alert(err,retcode)
            channel_info = kcs_channel_info
            resource_type = "node:bmc:interface:kcs"
        elif self._channel_interface == self.LAN_IF:
            lan_channel_info = self._check_lan_if_alert(err,retcode)
            channel_info = lan_channel_info
            resource_type = "node:bmc:interface:rmcp"

        # kcs_interface_alert=True and self.lan_interface_alert=True when fault alert raised
        # retcode == 0 means ipmitool cmd executed successfully
        # when both condition satisfied raise falut resolved alert
        if self.channel_err and retcode == 0:
            alert_type = "fault_resolved"
            channel_status = "Server BMC is reachable"
            self.kcs_interface_alert = False
            self.lan_interface_alert = False
            self.channel_err = False

        if (self.kcs_interface_alert or self.lan_interface_alert)  and not self.channel_err:
            alert_type = "fault"
            self.channel_err = True
            channel_status = "Server BMC is unreachable, possible cause: " + err

        if self.CHANNEL_INFO:
            channel_info = self.CHANNEL_INFO

        resource_id = channel_info.get('Channel Medium Type')
        severity_reader = SeverityReader()

        info = {
                "site_id": self._site_id,
                "rack_id": self._rack_id,
                "node_id": self._node_id,
                "cluster_id":self._cluster_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "event_time": epoch_time
            }

        specific_info = {
                "event": channel_status,
                "channel info": channel_info
            }

        if channel_info.get('Channel Medium Type'):
            if_type = channel_info.get('Channel Medium Type')
            if if_type == "802.3 LAN":
                specific_info["bmc_lan_user"] = self._bmc_user

        if alert_type is not None:
            severity = severity_reader.map_severity(alert_type)
            self._send_json_msg(resource_type, alert_type, severity, info, specific_info)

    def _check_kcs_if_alert(self,err,retcode):

        KCS_CHANNEL_INFO = {"Channel Medium Type": "System Interface","Channel Protocol Type": "KCS",
                            "Session Support": "session-less", "Active Session Count": "0", "Protocol Vendor ID": "7154"}

        if retcode != 0:
            # TODO: search for error codes which ipmitool returns in case of channel error
            if err in self.KCS_ERRS:
                self.kcs_interface_alert = True

        return KCS_CHANNEL_INFO

    def _check_lan_if_alert(self,err,retcode):

        LAN_CHANNEL_INFO = {"Channel Medium Type": "802.3 LAN","Channel Protocol Type": "IPMB-1.0",
                            "Session Support": "multi-session","Active Session Count": "1","Protocol Vendor ID": "7154"}

        if retcode !=0:
            if err in self.RMCP_ERRS:
                self.lan_interface_alert = True

        return LAN_CHANNEL_INFO

    def read_data(self):
        return self.sel_event_info

    def _get_sensor_list_by_type(self, sensor_type):
        """get list of sensors of type 'sensor_type'
           Returns a list of tuples, of which
           the first element is the sensor id and
           the second is the number."""

        sensor_list_out, retcode = self._run_ipmitool_subcommand(f"sdr type '{sensor_type}'")
        out = []

        if retcode != 0:
            if isinstance(sensor_list_out, tuple):
                sensor_list_out = [val for val in sensor_list_out if val]
            msg = f"ipmitool sdr type command failed: {b''.join(sensor_list_out)}"
            logger.warning(msg)
            return out

        sensor_list = b''.join(sensor_list_out).decode(self.IPMI_ENCODING).split("\n")

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

        sensor_list_out, retcode = self._run_ipmitool_subcommand(f"sdr entity '{entity_id}'")
        if retcode != 0:
            if isinstance(sensor_list_out, tuple):
                sensor_list_out = [val for val in sensor_list_out if val]
            msg = f"ipmitool sdr entity command failed: {b''.join(sensor_list_out)}"
            logger.error(msg)
            return
        sensor_list = b''.join(sensor_list_out).decode(self.IPMI_ENCODING).split("\n")

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
        props_list_out, retcode = self._run_ipmitool_subcommand(f"sdr get '{sensor_id}'")
        if retcode != 0:
            if isinstance(props_list_out, tuple):
                props_list_out = [val for val in props_list_out if val]
            msg = f"ipmitool sensor get command failed: {b''.join(props_list_out)}"
            logger.warning(msg)
            return
        props_list = b''.join(props_list_out).decode(self.IPMI_ENCODING).split("\n")

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
        props_list_out, retcode = self._run_ipmitool_subcommand(f"sensor get '{sensor_id}'")
        if retcode != 0:
            if isinstance(props_list_out, tuple):
                props_list_out = [val for val in props_list_out if val]
            msg = f"ipmitool sensor get command failed: {b''.join(props_list_out)}"
            logger.warning(msg)
            return (False, False)
        props_list = b''.join(props_list_out).decode(self.IPMI_ENCODING).split("\n")
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

        threshold_event = event.split(" ")
        threshold = threshold_event[len(threshold_event)-1]

        if status.lower() == "deasserted" and event.lower() == "fully redundant":
            alert_type = "fault"
        elif status.lower() == "asserted" and event.lower() == "fully redundant":
            alert_type = "fault_resolved"
        elif threshold.lower() in ['low', 'high']:
            alert_type = f"threshold_breached:{threshold}"

        sensor_name = self.sensor_id_map[self.TYPE_FAN][sensor_id]

        fan_common_data, fan_specific_data, fan_specific_data_dynamic = self._get_sensor_props(sensor_name)

        for key in list(fan_specific_data):
            if key not in fan_specific_list:
                del fan_specific_data[key]

        fan_info = fan_specific_data
        fan_info.update({"fru_id" : device_id, "event" : event})
        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_FAN
        severity_reader = SeverityReader()
        if alert_type:
            severity = severity_reader.map_severity(alert_type)
            if threshold.lower() in ['low', 'high'] and status.lower() == "deasserted":
                severity = "informational"
        else:
            # Else section will handle some unknown as well as known events like
            # "State Asserted", "State Deasserted" or "Sensor Reading" and also it is
            # keeping default severity and alert_type for those events.
            alert_type = "miscellaneous"
            severity = "informational"

        fru_info = {    "site_id": self._site_id,
                        "rack_id": self._rack_id,
                        "node_id": self._node_id,
                        "cluster_id":self._cluster_id ,
                        "resource_type": resource_type,
                        "resource_id": sensor_name,
                        "event_time": self._get_epoch_time_from_date_and_time(date, _time)
                    }

        if is_last:
            fan_info.update(fan_specific_data_dynamic)

        self._send_json_msg(resource_type, alert_type, severity, fru_info, fan_info)
        self._log_IEM(resource_type, alert_type, severity, fru_info, fan_info)

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
            ("Presence detected", "Asserted"): ("insertion","informational"),
            ("Presence detected", "Deasserted"): ("missing","critical"),
        }

        sensor_id = self.sensor_id_map[self.TYPE_PSU_SUPPLY][sensor_num]
        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_PSU
        info = {
            "site_id": self._site_id,
            "rack_id": self._rack_id,
            "node_id": self._node_id,
            "cluster_id": self._cluster_id,
            "resource_type": resource_type,
            "resource_id": sensor,
            "event_time": self._get_epoch_time_from_date_and_time(date, _time)
        }

        try:
            (alert_type, severity) = alerts[(event, status)]
        except KeyError:
            logger.error(f"Unknown event: {event}, status: {status}")
            return

        dynamic, static = self._get_sensor_sdr_props(sensor_id)
        specific_info = {}
        specific_info["fru_id"] = sensor
        specific_info["event"] = event
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

        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
        self._log_IEM(resource_type, alert_type, severity, info, specific_info)

    def _parse_psu_unit_info(self, index, date, _time, sensor, sensor_num, event, status, is_last):
        """Parse out PSU related changes that gets reflected in the ipmi sel list"""

        alerts = {

            ("240VA power down", "Asserted"): ("fault", "critical"),
            ("240VV power down", "Deasserted"): ("fault_resolved", "informational"),
            ("AC lost", "Asserted"): ("fault", "critical"),
            ("AC lost", "Deasserted"): ("fault_resolved", "informational"),
            ("Failure detected", "Asserted"): ("fault", "critical"),
            ("Failure detected", "Deasserted"): ("fault_resolved", "informational"),
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

        info = {
            "site_id": self._site_id,
            "rack_id": self._rack_id,
            "node_id": self._node_id,
            "cluster_id": self._cluster_id,
            "resource_type": resource_type,
            "resource_id": sensor,
            "event_time": self._get_epoch_time_from_date_and_time(date, _time)
        }

        try:
            (alert_type, severity) = alerts[(event, status)]
        except KeyError:
            logger.error(f"Unknown event: {event}, status: {status}")
            return

        dynamic, static = self._get_sensor_sdr_props(sensor_id)
        specific_info = {}
        specific_info["fru_id"] = sensor
        specific_info["event"] = event
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

        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
        self._log_IEM(resource_type, alert_type, severity, info, specific_info)

    def _parse_disk_info(self, index, date, _time, sensor, sensor_num, event, status, is_last):
        """Parse out Disk related changes that gets reaflected in the ipmi sel list"""

        sensor_id = self.sensor_id_map[self.TYPE_DISK][sensor_num]

        common, specific, specific_dynamic = self._get_sensor_props(sensor_id)
        if common:
            disk_sensors_list = self._get_sensor_list_by_entity(common['Entity ID'])
            disk_sensors_list.remove(sensor_id)

            if not specific:
                specific = {"States Asserted": "N/A", "Sensor Type (Discrete)": "N/A"}
            specific_info = specific
            alert_severity_dict = {
                ("Drive Present", "Asserted"): ("insertion", "informational"),
                ("Drive Present", "Deasserted"): ("missing", "critical"),
                }

            resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_DISK
            info = {
                "site_id": self._site_id,
                "rack_id": self._rack_id,
                "node_id": self._node_id,
                "cluster_id": self._cluster_id,
                "resource_type": resource_type,
                "resource_id": sensor,
                "event_time": self._get_epoch_time_from_date_and_time(date, _time)
            }
            if (event, status) in alert_severity_dict:
                alert_type = alert_severity_dict[(event, status)][0]
                severity   = alert_severity_dict[(event, status)][1]
            else:
                alert_type = "fault"
                severity   = "informational"
            specific_info["fru_id"] = sensor
            specific_info["event"] = f"{event} - {status}"

            if is_last:
                specific_info.update(specific_dynamic)

            for key in ['Deassertions Enabled', 'Assertions Enabled',
                        'Assertion Events', 'States Asserted']:
                try:
                    specific_info[key] = re.sub(',  +', ', ', re.sub('[\[\]]','', \
                        specific_info[key]).replace('\n',','))
                except KeyError:
                    pass

            self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
            self._log_IEM(resource_type, alert_type, severity, info, specific_info)

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

    def _log_IEM(self, resource_type, alert_type, severity, info, specific_info):
        """Sends an IEM to logging msg handler"""

        json_data = json.dumps({
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
            }, sort_keys=True)

        # Send the event to node data message handler to generate json message and send out
        internal_json_msg = json.dumps(
                {'actuator_request_type': {'logging': {'log_level': 'LOG_WARNING', 'log_type': 'IEM', 'log_msg': f'{json_data}'}}})

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

    def _get_host_id(self):
        return socket.getfqdn()

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
        return str(int(time.mktime(timestamp)))

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
