import abc
import subprocess

from framework.utils.ipmi import IPMI


class IPMITool(IPMI):
    """Concrete singleton class dervied from IPMI base class which implements
       functionality using ipmitool utility
    """
    _instance = None
    IPMITOOL = "sudo /usr/bin/ipmitool"

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
        """
        raise NotImplementedError()

    def get_sensor_sdr_props(self, sensor_id):
        """Returns sensor software data record based on sensor id of a FRU
           using ipmitool utility
           ipmitool sdr get 'sensor_id'
           Returns FRU instance specific information
        """
        raise NotImplementedError()

    def get_sensor_props(self):
        """Returns individual sensor instance properties based on
           sensor id using ipmitool utility
           ipmitool sensor get "Sys Fan 1A"
           Returns FRU instance specific information
        """
        raise NotImplementedError()

    def _run_ipmitool_sub_command(self, sub_command, grep_args=None):
        """executes ipmitool sub-commands using python subprocess module,
           and optionally greps the output
        """
        command = IPMITool.IPMITOOL + ' ' + sub_command
        if grep_args is not None:
            command += " | grep " + grep_args
        process = subprocess.Popen(command, shell=True,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        result = process.communicate()
        return result, process.returncode


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
        for key,value in globals().iteritems():
            if key.lower() == implementor.lower():
                return globals()[key]()
        return None
