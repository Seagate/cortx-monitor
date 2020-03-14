import os
import subprocess

from framework.utils.ipmi import IPMI
from framework.utils.service_logging import logger


class IPMITool(IPMI):
    """Concrete singleton class dervied from IPMI base class which implements
       functionality using ipmitool utility
    """
    _instance = None
    IPMITOOL = "sudo /usr/bin/ipmitool "
    IPMISIMTOOL = "/usr/bin/ipmisimtool "

    def __new__(cls):
        """new method"""
        if cls._instance is None:
            cls._instance = super(IPMITool, cls).__new__(cls)
        return cls._instance

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
        sensor_list_out, retcode = self._run_ipmitool_subcommand(f"sdr type '{fru_type.title()}'")
        if retcode != 0:
            msg = "ipmitool sdr type command failed: {0}".format(b''.join(sensor_list_out))
            logger.error(msg)
            return
        sensor_list = b''.join(sensor_list_out).decode("utf-8").split("\n")

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
        props_list_out, retcode = self._run_ipmitool_subcommand("sensor get '{0}'".format(sensor_id))
        if retcode != 0:
            msg = "ipmitool sensor get command failed: {0}".format(b''.join(props_list_out))
            logger.error(msg)
            return (False, False)
        props_list = b''.join(props_list_out).decode("utf-8").split("\n")
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

    def _run_command(self, command, out_file=subprocess.PIPE):
        """executes commands"""
        process = subprocess.Popen(command, shell=True, stdout=out_file, stderr=subprocess.PIPE)
        result = process.communicate()
        return result, process.returncode

    def _run_ipmitool_subcommand(self, subcommand, grep_args=None, out_file=subprocess.PIPE):
        """executes ipmitool sub-commands, and optionally greps the output"""

        # A dummy file path check to select ipmi simulator if
        # simulator is required, otherwise default ipmitool.
        if os.path.exists("/tmp/activate_ipmisimtool"):
            res, retcode = self._run_command(command=self.IPMISIMTOOL)
            if retcode == 0:
                self.IPMITOOL = self.IPMISIMTOOL
                logger.info("IPMI simulator is activated")

        command = self.IPMITOOL + subcommand
        if grep_args is not None:
            command += " | grep "
            if isinstance(grep_args, list):
                grep_args_str = ""
                for arg in grep_args:
                    grep_args_str = "'{}' ".format(arg)
                command += grep_args_str
            else:
                command += "'{}'".format(grep_args)
        res, retcode = self._run_command(command, out_file)

        return res, retcode


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
