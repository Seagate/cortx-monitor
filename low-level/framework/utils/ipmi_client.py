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

import re
import os
import subprocess
import shlex

from framework.utils.ipmi import IPMI
from framework.utils.service_logging import logger
from cortx.utils.process import SimpleProcess
from framework.utils.conf_utils import (Conf, SSPL_CONF, GLOBAL_CONF,
    BMC_CHANNEL_IF, BMC_INTERFACE, BMC_IP_KEY, BMC_USER_KEY, BMC_SECRET_KEY,
    MACHINE_ID, NODE_ID_KEY)
from framework.utils import encryptor
from framework.base.sspl_constants import ServiceTypes
from framework.utils.store_factory import file_store
from framework.base.sspl_constants import DATA_PATH

# Override default store
store = file_store


class IPMITool(IPMI):
    """Concrete singleton class dervied from IPMI base class which implements
       functionality using ipmitool utility
    """
    _instance = None
    NAME = "IPMITOOL"
    IPMITOOL = "sudo /usr/bin/ipmitool "
    IPMISIMTOOL = "/usr/bin/ipmisimtool "
    IPMI_ENCODING = 'utf8'
    MANUFACTURER = "Manufacturer Name"
    SYSTEM_IF = "system"
    LAN_IF = "lan"
    _node_id = Conf.get(GLOBAL_CONF, NODE_ID_KEY, 'SN01')
    ACTIVE_INTERFACE = f"{DATA_PATH}server/ACTIVE_BMC_IF_{_node_id}"
    ACTIVE_IPMI_TOOL = None
    VM_ERROR = 'Could not open device at'
    RMCP_ERRS = ("Unable to establish LAN session",
                 "Unable to establish IPMI v1.5 / RMCP session",
                 "Unable to establish IPMI v2 / RMCP+ session",
                 "connection timeout","session timeout",
                 "driver timeout","message timeout",
                 "Address lookup for -U failed","BMC busy","invalid user name",
                 "password invalid","password verification timeout",
                 "k_g invalid","privilege level insufficient",
                 "privilege level cannot be obtained for this user",
                 "authentication type unavailable for attempted privilege level")
    KCS_ERRS = ("could not find inband device", "driver timeout")

    def __new__(cls):
        """new method"""
        if cls._instance is None:
            cls._instance = super(IPMITool, cls).__new__(cls)
        return cls._instance

    def get_manufacturer_name(self):
        """Returns node server manufacturer name.
            Example: Supermicro, Intel Corporation, DELL Inc
        """
        manufacturer_name = ""
        cmd = "bmc info"
        output, _, rc = self._run_ipmitool_subcommand(cmd)
        if rc == 0:
            search_res = re.search(
                r"%s[\s]+:[\s]+([\w]+)(.*)" % self.MANUFACTURER, output)
            if search_res:
                manufacturer_name = search_res.groups()[0]
        return manufacturer_name

    def get_sensor_list_by_entity(self, entity_id):
        """Returns the sensor list based on entity id using ipmitool utility
           ipmitool sdr entity '<entity_id>'.
           Example of output form 'sdr entity 29.4' command:
           Sys Fan 2B       | 33h | ok  | 29.4 | 5332 RPM
           ( sensor_id | sensor_num | status | entity_id |
            <FRU Specific attribute> )
        """
        raise NotImplementedError()

    def get_sensor_list_by_type(self, fru_type):
        """Returns the sensor list based on FRU type using ipmitool utility
           ipmitool sdr type '<FRU>'.
           Example of output form 'sdr type 'Fan'' command:
           Sys Fan 2B       | 33h | ok  | 29.4 | 5332 RPM
           ( sensor_id | sensor_num | status | entity_id |
            <FRU Specific attribute> )
            Params : self, fru_type
            Output Format : List of Tuple
            Output Example : [(HDD 1 Status, F1, ok, 4.2, Drive Present),]
        """
        sensor_list_out, error, retcode = self._run_ipmitool_subcommand(f"sdr type '{fru_type.title()}'")
        if retcode != 0:
            msg = "ipmitool sdr type command failed: {0}".format(error)
            logger.warning(msg)
            return
        sensor_list = sensor_list_out.split("\n")

        out = []
        for sensor in sensor_list:
            if sensor == "":
                break
            # Example of output form 'sdr type' command:
            # Sys Fan 2B       | 33h | ok  | 29.4 | 5332 RPM
            # PS1 1a Fan Fail  | A0h | ok  | 29.13 |
            # HDD 1 Status     | F1h | ok  |  4.2 | Drive Present
            fields_list = [ f.strip() for f in sensor.split("|")]
            sensor_id, sensor_num, status, entity_id, reading  = fields_list
            sensor_num = sensor_num.strip("h").lower()

            out.append((sensor_id, sensor_num, status, entity_id, reading))
        return out

    def get_sensor_sdr_props(self, sensor_id):
        """Returns sensor software data record based on sensor id of a FRU
           using ipmitool utility
           ipmitool sdr get 'sensor_id'
           Returns FRU instance specific information
        """
        raise NotImplementedError()

    def get_sensor_props(self, sensor_id):
        """Returns individual sensor instance properties based on
           sensor id using ipmitool utility
           ipmitool sensor get "Sys Fan 1A"
           Returns FRU instance specific information
           Params : self, sensor_id
           Output Format : Tuple inside dictionary of common and specific data
           Output Example : ({common dict data},{specific dict data})
        """
        props_list_out, error, retcode = \
            self._run_ipmitool_subcommand(f"sensor get '{sensor_id}'")
        if retcode != 0:
            msg = f"ipmitool sensor get command failed: {error}"
            logger.warning(msg)
            err_response = {sensor_id: {"ERROR": msg}}
            return (False, err_response)
        props_list = props_list_out.split("\n")
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
        for c in (set(specific.keys()) & common_props):
            common[c] = specific[c]
            del specific[c]

        return (common, specific)

    def get_fru_list_by_type(self, fru_list, sensor_id_map):
        """Returns FRU instances list using ipmitool sdr type command
            Params : self, fru_list, sensor_id_map
            Output Format : dictionary which have fru_instance mapping with fru id
            Output Example : {"drive slot / bay":{0:"HDD 1 Status",}, "fan":{}}
        """
        for fru in fru_list:
            fru_detail = self.get_sensor_list_by_type(fru)
            sensor_id_map[fru] = {fru_detail.index(fru): fru[0].strip()
                for fru in fru_detail}
        return sensor_id_map

    def _run_ipmitool_subcommand(self, subcommand, grep_args=None):
        """Executes ipmitool sub-commands, and optionally greps the output."""
        self.ACTIVE_IPMI_TOOL = self.IPMITOOL
        host_conf_cmd = ""

        # Set ipmitool to ipmisimtool if activated.
        if os.path.exists(f"{DATA_PATH}/server/activate_ipmisimtool"):
            cmd = self.IPMISIMTOOL + " sel info"
            _, _, retcode = SimpleProcess(cmd).run()
            if retcode in [0, 2]:
                self.ACTIVE_IPMI_TOOL = self.IPMISIMTOOL
                logger.info("IPMI simulator is activated.")

        # Fetch channel info from config file and cache.
        _channel_interface = Conf.get(SSPL_CONF, "%s>%s" %
                                (BMC_INTERFACE, BMC_CHANNEL_IF))

        _active_interface = store.get(self.ACTIVE_INTERFACE, None)

        # Set host_conf_cmd based on channel info.
        if _channel_interface == self.LAN_IF and \
           _active_interface == self.LAN_IF and \
           self.ACTIVE_IPMI_TOOL != self.IPMISIMTOOL:
            bmc_ip = Conf.get(GLOBAL_CONF, BMC_IP_KEY, '')
            bmc_user = Conf.get(GLOBAL_CONF, BMC_USER_KEY, 'ADMIN')
            bmc_secret = Conf.get(GLOBAL_CONF, BMC_SECRET_KEY, 'ADMIN')

            decryption_key = encryptor.gen_key(MACHINE_ID,
                                               ServiceTypes.SERVER_NODE.value)
            bmc_pass = encryptor.decrypt(decryption_key,
                                         bmc_secret, self.NAME)

            host_conf_cmd = f"-I lanplus -H {bmc_ip} -U {bmc_user} -P {bmc_pass}"

        # generate the final cmd and execute on shell.
        command = " ".join([self.ACTIVE_IPMI_TOOL, host_conf_cmd, subcommand])
        command = shlex.split(command)

        out, error, retcode = SimpleProcess(command).run()

        # Decode bytes encoded strings.
        if not isinstance(out, str):
            out = out.decode(self.IPMI_ENCODING)
        if not isinstance(error, str):
            error = error.decode(self.IPMI_ENCODING)

        # Grep the output as per grep_args provided.
        if grep_args is not None and retcode == 0:
            final_list = []
            for l in out.split('\n'):
                if re.search(grep_args, l) is not None:
                    final_list += [l]
            out = '\n'.join(final_list)

        # Assign error_msg to err from output
        if retcode and not error:
            out, error = error, out
        # Remove '\n' from error, for matching errors to error stings.
        if error:
            error = error.replace('\n', '')

        return out, error, retcode

class IpmiFactory(object):
    """Factory class which returns instance of specific IPMI related
       class based on value from config
    """
    def __init__(self):
        """init method"""
        super(IpmiFactory, self).__init__()

    def get_implementor(self, implementor):
        """Returns instance of the class based on value from config file
        """
        for key,value in list(globals().items()):
            if key.lower() == implementor.lower():
                return globals()[key]()
        return None
