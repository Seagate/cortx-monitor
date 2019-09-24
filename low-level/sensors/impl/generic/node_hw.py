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
import tempfile

from zope.interface import implements

from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from message_handlers.logging_msg_handler import LoggingMsgHandler

from framework.base.debug import Debug
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.config_reader import ConfigReader
from framework.utils.service_logging import logger
from sensors.INode_hw import INodeHWsensor

IPMITOOL = "sudo /usr/bin/ipmitool"

class NodeHWsensor(ScheduledModuleThread, InternalMsgQ):
    """Obtains data about the FRUs and logical sensors and updates
       if any state change occurs"""

    implements(INodeHWsensor)

    SENSOR_NAME = "NodeHWsensor"
    PRIORITY = 1

    sel_event_info = ""

    TYPE_PSU = 'Power Supply'

    CONF_FILE = "/etc/sspl.conf"
    SYSINFO = "SYSTEM_INFORMATION"
    DATA_PATH_KEY = "data_path"
    DATA_PATH_VALUE_DEFAULT = "/var/sspl/data"

    CACHE_DIR  = "server"
    # This file stores the last index from the SEL list for which we have issued an event.
    INDEX_FILE = "last_sel_index"
    LIST_FILE  = "sel_list"

    UPDATE_CREATE_MODE = "w+"
    UPDATE_ONLY_MODE   = "r+"

    @staticmethod
    def name():
        """@return: name of the module."""
        return NodeHWsensor.SENSOR_NAME

    def __init__(self):
        super(NodeHWsensor, self).__init__(self.SENSOR_NAME.upper(), self.PRIORITY)
        self.host_id = None

        # Validate configuration file for required valid values
        try:
            self.conf_reader = ConfigReader(self.CONF_FILE)

        except (IOError, ConfigReader.Error) as err:
            logger.error("[ Error ] when validating the config file {0} - {1}"\
                 .format(self.CONF_FILE, err))

    def _get_file(self, name):
        if os.path.exists(name):
            mode = self.UPDATE_ONLY_MODE
        else:
            mode = self.UPDATE_CREATE_MODE
        return open(name, mode)

    def _initialize_cache(self):
        data_dir =  self.conf_reader._get_value_with_default(
            self.SYSINFO, self.DATA_PATH_KEY, self.DATA_PATH_VALUE_DEFAULT)
        cache_dir = os.path.join(data_dir, self.CACHE_DIR)

        if not os.path.exists(cache_dir):
            logger.info("Creating cache dir: {0}".format(cache_dir))
            os.makedirs(cache_dir)
        logger.info("Using cache dir: {0}".format(cache_dir))

        index_file_name = os.path.join(cache_dir, self.INDEX_FILE)
        self.index_file = self._get_file(index_file_name)

        if os.path.getsize(self.index_file.name) == 0:
            self._write_index_file("0")
        # Now self.index_file has a valid sel index in it

        list_file_name = os.path.join(cache_dir, self.LIST_FILE)
        self.list_file = self._get_file(list_file_name)

    def _write_index_file(self, index):
        self.index_file.seek(0)
        self.index_file.truncate()
        self.index_file.write("{0}\n".format(index))
        self.index_file.flush()

    def _read_index_file(self):
        self.index_file.seek(0)
        index_line = self.index_file.readline()
        return int(index_line, base=16)

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(NodeHWsensor, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(NodeHWsensor, self).initialize_msgQ(msgQlist)

        self._initialize_cache()

        self.sensor_id_map = dict()
        self.sensor_id_map[self.TYPE_PSU] = { sensor_num: sensor_id
            for (sensor_id, sensor_num) in self._get_sensor_list_by_type(self.TYPE_PSU)}

    def _update_list_file(self):
        (tmp_fd, tmp_name) = tempfile.mkstemp()
        sel_out, retcode = self._run_ipmitool_subcommand("sel list", out_file=tmp_fd)
        if retcode != 0:
            msg = "ipmitool sel list command failed: {0}".format(''.join(sel_out))
            logger.error(msg)
            raise Exception(msg)

        # os.rename() is an atomic operation, which means that even if we crash
        # the SEL list in self.list_file will always be in a consistent state.
        list_file_name = self.list_file.name
        os.rename(tmp_name, list_file_name)
        self.list_file.close()
        self.list_file = open(list_file_name, self.UPDATE_ONLY_MODE)


    def run(self):
        """Run the sensor on its own thread"""

        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        # self._set_debug(True)
        # self._set_debug_persist(True)

        try:
            # Check for a change in ipmi sel list and notify the node data msg handler
            if os.path.getsize(self.list_file.name) != 0:
                # If the SEL list file is not empty, that means that some of the processing
                # from the last iteration is incomplete. Complete that
                # before getting the new SEL events.
                self._notify_NodeDataMsgHandler()
            self._update_list_file()
            self._notify_NodeDataMsgHandler()
        except Exception as ae:
            logger.exception(ae)

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()
        self._scheduler.enter(30, self._priority, self.run, ())

    def _get_sel_list(self):
        index = self._read_index_file()

        # TODO: See if the following 2 loops can be reduced to
        # a single loop using mmap() and a fixed file format like
        # the one produced by the 'ipmitool sel file' or
        # 'ipmitool sel writeraw' commands.
        found = False
        self.list_file.seek(0, os.SEEK_SET)
        for line in self.list_file:
            if not found:
                if line.split("|")[0] == " {0:x} ".format(index):
                    found = True
                continue

            yield line

        if not found:
            # This can mean one of a few things:
            # 1. The SEL has been cleared beyond the last index we saw
            # 2. It has rotated to beyond the last index we saw
            # 3. self.list_file is empty
            self.list_file.seek(0, os.SEEK_SET)
            for line in self.list_file:
                yield line


    def _notify_NodeDataMsgHandler(self):
        """See if there is any new event gets generated in the sel and notify
            node data message handler for generating JSON message"""

        # splitting up the attributes from the list generated in the IPMI sel
        for sel_event in self._get_sel_list():
            if sel_event == '':
                break

            # Separate out the components of the sel event
            # Sample sel event which gets parsed
            # 2 | 04/16/2019 | 05:29:09 | Fan #0x30 | Lower Non-critical going low  | Asserted
            index, date, time, device_id, event, status = [
                attr.strip() for attr in sel_event.split("|") ]

            if 'Fan ' in device_id:
                self._parse_fan_info(index, date, time, device_id, event)
            elif 'Power Supply ' in device_id:
                self._parse_psu_info(index, date, time, device_id, event)

            self._write_index_file(index)

        self.list_file.seek(0)
        self.list_file.truncate()

    def _run_command(self, command, out_file=subprocess.PIPE):
        """executes commands"""

        process = subprocess.Popen(command, shell=True, stdout=out_file, stderr=subprocess.PIPE)
        result = process.communicate()
        return result, process.returncode

    def _run_ipmitool_subcommand(self, subcommand, grep_args=None, out_file=subprocess.PIPE):
        """executes ipmitool sub-commands, and optionally greps the output"""

        command = IPMITOOL + ' ' + subcommand
        if grep_args is not None:
            command += " | grep " + grep_args
        return self._run_command(command, out_file)

    def read_data(self):
        return self.sel_event_info

    def _get_sensor_list_by_type(self, sensor_type):
        """get list of sensors of type 'sensor_type'
           Returns a list of tuples, of which
           the first element is the sensor id and
           the second is the number."""

        sensor_list_out, retcode = self._run_ipmitool_subcommand("sdr type '{0}'".format(sensor_type))
        if retcode != 0:
            msg = "ipmitool sdr type command failed: {0}".format(''.join(sensor_list_out))
            logger.error(msg)
            return
        sensor_list = ''.join(sensor_list_out).split("\n")

        out = []
        for sensor in sensor_list:
            if sensor == "":
                break
            # Example of output form 'sdr type' command:
            # Sys Fan 2B       | 33h | ok  | 29.4 | 5332 RPM
            # PS1 1a Fan Fail  | A0h | ok  | 29.13 |
            fields_list = [ f.strip() for f in sensor.split("|")]
            sensor_id, sensor_num, status, entity_id, reading  = fields_list
            sensor_num = sensor_num.strip("h").lower()

            out.append((sensor_id, sensor_num))
        return out

    def _get_sensor_list_by_entity(self, entity_id):
        """get list of sensors belonging to entity 'entity_id'
           Returns a list of sensor IDs"""

        sensor_list_out, retcode = self._run_ipmitool_subcommand("sdr entity '{0}'".format(entity_id))
        if retcode != 0:
            msg = "ipmitool sdr entity command failed: {0}".format(''.join(sensor_list_out))
            logger.error(msg)
            return
        sensor_list = ''.join(sensor_list_out).split("\n")

        out = []
        for sensor in sensor_list:
            if sensor == '':
                continue
            # Output from 'sdr entity' command is same as from 'sdr type' command.
            fields_list = [f.strip() for f in sensor.split("|")]
            sensor_id, sensor_num, status, entity_id, reading = fields_list
            sensor_num = sensor_num.strip("h").lower()

            out.append(sensor_id)
        return out


    def _get_sensor_props(self, sensor_id):
        """get all the properties of a sensor.
           Returns a tuple (common, specific) where
           common is a dict of common sensor properties and
             their values for this sensor, and
           specific is a dict of the properties specific to this sensor"""
        props_list_out, retcode = self._run_ipmitool_subcommand("sensor get '{0}'".format(sensor_id))
        if retcode != 0:
            msg = "ipmitool sensor get command failed: {0}".format(''.join(sel_out))
            logger.error(msg)
            return
        props_list = ''.join(props_list_out).split("\n")
        props_list = props_list[1:] # The first line is 'Locating sensor record...'

        specific = {}
        curr_key = None
        for prop in props_list:
            if prop == '':
                continue
            if ':' in prop:
                curr_key, val = [f.strip() for f in prop.split(":")]
                specific[curr_key] = val
            else:
                specific[curr_key] += "\n" + prop

        common = {}
        common_props = {
            'Sensor ID',
            'Entity ID',
        }
        # Whatever keys from common_props are present,
        # move them to the 'common' dict
        for c in (specific.viewkeys() & common_props):
            common[c] = specific[c]
            del specific[c]

        return (common, specific)

    def _parse_fan_info(self, index, date, time, device_id, event):
        """Parse out Fan realted changes that gets reaflected in the ipmi sel list"""

        fru_id = device_id.split()[1]

        # event will be "Lower critical going low'. Splitting the event
        # name which is critical in order to get its individual value
        event_name = event.split(' ')[1] + ' ' + event.split(' ')[2]

        # Getting the Actual Fan list in order to get individual values of Particular Fan
        command = IPMITOOL + ' ' + "sensor list | grep Fan"
        fan_list = self._run_command(command)
        for fan in ''.join(fan_list[0]).split("\n"):
                self._fans = []
                fan_name = ''.join(fan).strip(' ').split("|")

                # command will be sudo /usr/bin/ipmitool sensor get 'Sys Fan 1A' | grep '0x30'
                command = IPMITOOL + ' ' + "sensor get '"'{0}'"' | grep '"'{1}'"'".format(fan_name[0].strip(' '), fru_id)
                res, retcode = self._run_command(command)
                fan_attributes = ['status', 'sensor reading', event_name]
                if retcode == 0:

                        # Fetching the individual values. Command will be sudo /usr/bin/ipmitool sensor get 'Sys Fan 1A' |
                        # grep -wi -e 'status' -e 'sensor reading' -e 'Critical'
                        command = IPMITOOL + ' ' + "sensor get '"'{0}'"' | grep -wi -e '"'{1}'"' -e '"'{2}'"' -e '"'{3}'"'" \
                        .format(fan_name[0].strip(' '), *fan_attributes)
                        res1 = self._run_command(command)
                        sensor_reading = ''.join(res1[0]).split("\n")[0][15:].strip(': ')
                        status = ''.join(res1[0]).split("\n")[1][8:].strip(': ')
                        event_reading = ''.join(res1[0]).split("\n")[2][19:].strip(': ')

                        self._fan_msg = {
                                        "Fru Id": device_id,
                                        "event": event.strip(),
                                        "date": date,
                                        "time": time,
                                        "Status": status,
                                        "Sensor Reading": sensor_reading,
                                        event_name: event_reading
                                        }
                        self._fans.append(self._fan_msg)
                        self._send_json_msg("fans", self._fans)
                        self._log_IEM("fans", self._fans)
                        break

    def _parse_psu_info(self, index, date, time, sensor, event):
        """Parse out Fan realted changes that gets reaflected in the ipmi sel list"""

        sensor_num = re.match(self.TYPE_PSU + ' #0x([0-9a-f]+)', sensor).group(1)
        sensor_id = self.sensor_id_map[self.TYPE_PSU][sensor_num]

        common, specific = self._get_sensor_props(sensor_id)
        psu_sensors_list = self._get_sensor_list_by_entity(common['Entity ID'])
        psu_sensors_list.remove(sensor_id)

        info = {
            "date": date, "time": time,
            "sensor_id": sensor_id, "event": event,
            "fru_id": sensor
        }
        specific_info = specific

        resource_type = NodeDataMsgHandler.IPMI_RESOURCE_TYPE_PSU
        if 'Failure detected' in event:
            alert_type = "fault"
        else:
            alert_type = "information"

        if alert_type == "fault":
            severity = "critical"
        else:
            severity = "informational"


        self._send_json_msg(resource_type, alert_type, severity, info, specific_info)
        self._log_IEM(resource_type, alert_type, severity, info, specific_info)


    def _send_json_msg(self, resource_type, alert_type, severity, info, specific_info):
        """Transmit data to NodeDataMsgHandler which takes two arguments.
           device will be device name and data will consist of relevant data"""

        internal_json_msg = json.dumps({
            "sensor_response_type" : {
                "resource_type": resource_type,
                "alert_type": alert_type,
                "severity": severity,
                "info": info,
                "specific_info": specific_info
                }
            })

        # Send the event to node data message handler to generate json message and send out
        self._write_internal_msgQ(NodeDataMsgHandler.name(), internal_json_msg)

    def _log_IEM(self, resource_type, alert_type, severity, info, specific_info):
        """Sends an IEM to logging msg handler"""

        json_data = json.dumps({
            "sensor_response_type" : {
                "resource_type": resource_type,
                "alert_type": alert_type,
                "severity": severity,
                "info": info,
                "specific_info": specific_info
                }
            }, sort_keys=True)

        # Send the event to node data message handler to generate json message and send out
        internal_json_msg = json.dumps(
                {'actuator_request_type': {'logging': {'log_level': 'LOG_WARNING', 'log_type': 'IEM', 'log_msg': '{}'.format(json_data)}}})

        # Send the event to logging msg handler to send IEM message to journald
        self._write_internal_msgQ(LoggingMsgHandler.name(), internal_json_msg)

