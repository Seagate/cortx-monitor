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
  Description:       Obtains information about the node and makes it available.
 ****************************************************************************
"""

import errno
import math
import os
import re
import socket
import subprocess as sp
import threading
import time
from datetime import datetime

import psutil
from zope.interface import implementer

from framework.base.debug import Debug
from framework.base.global_config import GlobalConf
from framework.utils.config_reader import ConfigReader
from framework.utils.service_logging import logger
from framework.utils.sysfs_interface import SysFS
from framework.utils.tool_factory import ToolFactory
from sensors.INode_data import INodeData


@implementer(INodeData)
class NodeData(Debug):
    """Obtains data about the node and makes it available"""


    SENSOR_NAME = "NodeData"

    # conf attribute initialization
    PROBE = 'probe'

    @staticmethod
    def name():
        """@return: name of the module."""
        return NodeData.SENSOR_NAME

    def __init__(self):
        super(NodeData, self).__init__()

        self.host_id = socket.getfqdn()
        self._epoch_time = str(int(time.time()))
        # Total number of CPUs
        self.cpus = psutil.cpu_count()

        # Calculate the load averages on separate blocking threads
        self.load_1min_average  = []
        self.load_5min_average  = []
        self.load_15min_average = []
        self.prev_bmcip = None
        load_1min_avg  = threading.Thread(target=self._load_1min_avg).start()
        load_5min_avg  = threading.Thread(target=self._load_5min_avg).start()
        load_15min_avg = threading.Thread(target=self._load_15min_avg).start()

        self.conf_reader = ConfigReader()

        nw_fault_utility = GlobalConf().fetch_sspl_config(
            query_string = f"{self.name().capitalize()}>{self.PROBE}",
            default_val = "sysfs")

        self._utility_instance = None

        try:
            # Creating the instance of ToolFactory class
            self.tool_factory = ToolFactory()
            # Get the instance of the utility using ToolFactory
            self._utility_instance = self._utility_instance or \
                                self.tool_factory.get_instance(nw_fault_utility)
            if self._utility_instance:
                # Initialize the path as /sys/class/net/
                self.nw_interface_path = self._utility_instance.get_sys_dir_path('net')
        except KeyError as key_error:
            logger.error(f'NodeData, Unable to get the instance of {nw_fault_utility} Utility')
        except Exception as err:
            logger.error(f'NodeData, Problem occured while getting the instance of {nw_fault_utility}')

    def read_data(self, subset, debug, units="MB"):
        """Updates data based on a subset"""
        self._set_debug(debug)
        self._log_debug("read_data, subset: %s, units: %s" % (subset, units))

        try:
            # Determine the units factor value
            self.units_factor = 1
            if units == "GB":
                self.units_factor = 1000000000
            elif units == "MB":
                self.units_factor = 1000000
            elif units == "KB":
                self.units_factor = 1000

            # First call gethostname() to see if it returns something that looks like a host name,
            # if not then get the host by address
            # Find a meaningful hostname to be used
            self.host_id = socket.getfqdn()
            # getfqdn() function checks the socket.gethostname() to get the host name if it not available
            # then it try to find host name from socket.gethostbyaddr(socket.gethostname())[0] and return the
            # meaningful host name priviously we chking the this two conditions explicitly which is implicitly
            # doing by getfqdn() function. so removing the code and adding the getfqdn() function to get Hostname.

            self.local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')

            # Branch off and gather data based upon value sent into subset
            if subset == "host_update":
                self._get_host_update_data()

            elif subset == "local_mount_data":
                self._get_local_mount_data()

            elif subset == "cpu_data":
                self._get_cpu_data()

            elif subset == "if_data":
                self._get_if_data()

            elif subset == "disk_space_alert":
                self._get_disk_space_alert_data()

        except Exception as e:
            logger.exception(e)
            return False

        return True

    def _get_host_update_data(self):
        """Retrieves node information for the host_update json message"""
        logged_in_users = []
        uname_keys = ("sysname", "nodename", "version", "release", "machine")
        self.up_time         = int(psutil.boot_time())
        self.boot_time       = self._epoch_time
        self.uname           = dict(zip(uname_keys, os.uname()))
        self.total_memory = dict(psutil.virtual_memory()._asdict())
        self.process_count   = len(psutil.pids())
        for users in psutil.users():
            logged_in_users.append(dict(users._asdict()))
        self.logged_in_users = logged_in_users
        # Calculate the current number of running processes at this moment
        total_running_proc = 0
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['status'])
            if pinfo['status'] not in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD,
                                       psutil.STATUS_STOPPED, psutil.STATUS_IDLE,
                                       psutil.STATUS_SLEEPING):
                total_running_proc += 1
        self.running_process_count = total_running_proc

    def _get_local_mount_data(self):
        """Retrieves node information for the local_mount_data json message"""
        self.total_space = int(psutil.disk_usage("/")[0])//int(self.units_factor)
        self.free_space  = int(psutil.disk_usage("/")[2])//int(self.units_factor)
        self.total_swap  = int(psutil.swap_memory()[0])//int(self.units_factor)
        self.free_swap   = int(psutil.swap_memory()[2])//int(self.units_factor)
        self.free_inodes = int(100 - math.ceil((float(os.statvfs("/").f_files - os.statvfs("/").f_ffree) \
                             / os.statvfs("/").f_files) * 100))

    def _get_cpu_data(self):
        """Retrieves node information for the cpu_data json message"""
        cpu_core_usage_dict = dict()
        cpu_data = psutil.cpu_times_percent()
        self._log_debug("_get_cpu_data, cpu_data: %s %s %s %s %s %s %s %s %s %s" % cpu_data)

        self.csps           = 0  # What the hell is csps - cycles per second?
        self.user_time      = int(cpu_data[0])
        self.nice_time      = int(cpu_data[1])
        self.system_time    = int(cpu_data[2])
        self.idle_time      = int(cpu_data[3])
        self.iowait_time    = int(cpu_data[4])
        self.interrupt_time = int(cpu_data[5])
        self.softirq_time   = int(cpu_data[6])
        self.steal_time     = int(cpu_data[7])

        self.cpu_usage = psutil.cpu_percent(interval=1, percpu=False)
        # Array to hold data about each CPU core
        self.cpu_core_data = []
        index = 0
        while index < self.cpus:
            self._log_debug("_get_cpu_data, index: %s, 1 min: %s, 5 min: %s, 15 min: %s" %
                            (index,
                            self.load_1min_average[index],
                            self.load_5min_average[index],
                            self.load_15min_average[index]))

            cpu_core_data = {"coreId"      : index,
                             "load1MinAvg" : int(self.load_1min_average[index]),
                             "load5MinAvg" : int(self.load_5min_average[index]),
                             "load15MinAvg": int(self.load_15min_average[index]),
                             "ips" : 0
                             }
            self.cpu_core_data.append(cpu_core_data)
            index += 1

    def _get_if_data(self):
        """Retrieves node information for the if_data json message"""
        net_data = psutil.net_io_counters(pernic=True)
        # Array to hold data about each network interface
        self.if_data = []
        bmc_data = self._get_bmc_info()
        for interface, if_data in net_data.items():
            self._log_debug("_get_if_data, interface: %s %s" % (interface, net_data))
            nw_status = self._fetch_nw_status()
            nw_cable_conn_status = self.fetch_nw_cable_conn_status(interface)
            if_data = {"ifId" : interface,
                       "networkErrors"      : (net_data[interface].errin +
                                               net_data[interface].errout),
                       "droppedPacketsIn"   : net_data[interface].dropin,
                       "packetsIn"          : net_data[interface].packets_recv,
                       "trafficIn"          : net_data[interface].bytes_recv,
                       "droppedPacketsOut"  : net_data[interface].dropout,
                       "packetsOut"         : net_data[interface].packets_sent,
                       "trafficOut"         : net_data[interface].bytes_sent,
                       "nwStatus"           : nw_status[interface][0],
                       "ipV4"               : nw_status[interface][1],
                       "nwCableConnStatus"  : nw_cable_conn_status
                       }
            self.if_data.append(if_data)
        self.if_data.append(bmc_data)

    def _fetch_nw_status(self):
        nw_dict = {}
        nws = os.popen("ip --br a | awk '{print $1, $2, $3}'").read().split('\n')[:-1]
        for nw in nws:
            if nw.split(' ')[2]:
                ip = nw.split(' ')[2].split("/")[0]
            else:
                ip = ""
            nw_dict[nw.split(' ')[0]] = [nw.split(' ')[1], ip]
        logger.debug("network info going is : {}".format(nw_dict))
        return nw_dict

    def fetch_nw_cable_conn_status(self, interface):
        carrier_status = None
        try:
            carrier_status = self._utility_instance.fetch_nw_cable_status(self.nw_interface_path, interface)
        except Exception as e:
            if e == errno.ENOENT:
                logger.error(
                    "Problem occured while reading from nw carrier file:"
                    f" {self.nw_interface_path}/{interface}/carrier."
                    "file path doesn't exist")
            elif e == errno.EACCES:
                logger.error(
                    "Problem occured while reading from nw carrier file:"
                    f" {self.nw_interface_path}/{interface}/carrier."
                    "Not enough permission to read from the file.")
            elif e == errno.EPERM:
                logger.error(
                    "Problem occured while reading from nw carrier file:"
                    f" {self.nw_interface_path}/{interface}/carrier."
                    "Operation is not permitted.")
            else:
                logger.error(
                    "Problem occured while reading from nw carrier file:"
                    f" {self.nw_interface_path}/{interface}/carrier. Error: {e}")
        return carrier_status

    def _get_bmc_info(self):
        """
        nwCableConnection will be default UNKNOWN,
        Until solution to find bmc eth port cable connection status is found.
        """
        try:
            bmcdata = {'ifId': 'ebmc0', 'ipV4Prev': "", 'ipV4': "", 'nwStatus': "DOWN", 'nwCableConnStatus': 'UNKNOWN'}
            ipdata = sp.Popen("sudo ipmitool lan print", shell=True, stdout=sp.PIPE, stderr=sp.PIPE).communicate()[0].decode().strip()
            bmcip = re.findall("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ipdata)
            if bmcip:
                bmcip = bmcip[0]
                pingbmchost = "ping -c1 -W1 -q "+bmcip
                child = sp.Popen(pingbmchost.split(), stdout=sp.PIPE)
                streamdata = child.communicate()[0] #child must be communicated before fetching return code.
                retcode = child.returncode
                if self.prev_bmcip is not None and self.prev_bmcip != bmcip:
                    bmcdata['ipV4Prev'] = self.prev_bmcip
                    bmcdata['ipV4'] = bmcip
                    self.prev_bmcip = bmcip
                else:
                    self.prev_bmcip = bmcdata['ipV4Prev'] = bmcdata['ipV4'] = bmcip
                if retcode == 0:
                    bmcdata['nwStatus'] = "UP"
                else:
                    logger.warning("BMC Host:{0} is not reachable".format(bmcip))
        except Exception as e:
            logger.error("Exception occurs while fetching bmc_info:{}".format(e))
        return bmcdata

    def _get_disk_space_alert_data(self):
        """Retrieves node information for the disk_space_alert_data json message"""
        self.total_space = int(psutil.disk_usage("/")[0])//int(self.units_factor)
        self.free_space  = int(psutil.disk_usage("/")[2])//int(self.units_factor)
        self.disk_used_percentage  = psutil.disk_usage("/")[3]

    def _load_1min_avg(self):
        """Loop forever calculating the one minute average load"""
        # Initialize list to -1 indicating the time interval has not occurred yet
        index = 0
        while index < self.cpus:
            self.load_1min_average.append(-1)
            index += 1

        while True:
            # API call blocks for one minute and then returns the value
            self.load_1min_average = psutil.cpu_percent(interval=1, percpu=True)

    def _load_5min_avg(self):
        """Loop forever calculating the five minute average load"""
        # Initialize list to -1 indicating the time interval has not occurred yet
        index = 0
        while index < self.cpus:
            self.load_5min_average.append(-1)
            index += 1

        while True:
            # API call blocks for five minutes and then returns the value
            self.load_5min_average = psutil.cpu_percent(interval=5, percpu=True)

    def _load_15min_avg(self):
        """Loop forever calculating the fifteen minute average load"""
        # Initialize list to -1 indicating the time interval has not occurred yet
        index = 0
        while index < self.cpus:
            self.load_15min_average.append(-1)
            index += 1

        while True:
            # API call blocks for fifteen minutes and then returns the value
            self.load_15min_average = psutil.cpu_percent(interval=15, percpu=True)
