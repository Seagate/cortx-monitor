"""
 ****************************************************************************
 Filename:          node_data.py
 Description:       Obtains information about the node and makes it available.
 Creation Date:     06/10/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import os
import math
import datetime
import socket
import psutil
import threading

from datetime import datetime, timedelta

from framework.base.debug import Debug
from framework.utils.service_logging import logger

from zope.interface import implements
from sensors.INode_data import INodeData


class NodeData(Debug):
    """Obtains data about the node and makes it available"""

    implements(INodeData)

    SENSOR_NAME = "NodeData"


    @staticmethod
    def name():
        """@return: name of the module."""
        return NodeData.SENSOR_NAME

    def __init__(self):
        super(NodeData, self).__init__()

        # Total number of CPUs
        self._cpus = psutil.cpu_count()

        # Calculate the load averages on separate blocking threads     
        self._load_1min_average  = []
        self._load_5min_average  = []
        self._load_15min_average = []       
        load_1min_avg  = threading.Thread(target=self._load_1min_avg).start()
        load_5min_avg  = threading.Thread(target=self._load_5min_avg).start()
        load_15min_avg = threading.Thread(target=self._load_15min_avg).start()

    def read_data(self, subset, debug, units="MB"):
        """Updates data based on a subset"""
        self._set_debug(debug)
        self._log_debug("read_data, subset: %s, units: %s" % (subset, units))

        try:
            # Determine the units factor value
            self._units_factor = 1
            if units == "GB":
                self._units_factor = 1000000000
            elif units == "MB":
                self._units_factor = 1000000
            elif units == "KB":
                self._units_factor = 1000

            # First call gethostname() to see if it returns something that looks like a host name,
            # if not then get the host by address
            if socket.gethostname().find('.') >= 0:
                self._host_id = socket.gethostname()
            else:
                self._host_id = socket.gethostbyaddr(socket.gethostname())[0]

            self._local_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S %Z')

            # Branch off and gather data based upon value sent into subset
            if subset == "host_update":
                self._get_host_update_data()

            elif subset == "local_mount_data":
                self._get_local_mount_data()

            elif subset == "cpu_data":
                self._get_cpu_data()

            elif subset == "if_data":
                self._get_if_data()

        except Exception as e:
            logger.exception(e)
            return False

        return True

    def _get_host_update_data(self):
        """Retrieves node information for the host_update json message"""
        self._up_time         = int(psutil.boot_time())
        self._boot_time       = datetime.fromtimestamp(self._up_time).strftime('%Y-%m-%d %H:%M:%S %Z')
        self._uname           = str(os.uname()).replace("'", "")
        self._free_mem        = int(psutil.virtual_memory()[1])/self._units_factor        
        self._total_mem       = int(psutil.virtual_memory()[0])/self._units_factor
        self._free_mem_units  = "MB"
        self._total_mem_units = "MB"
        self._process_count   = len(psutil.get_pid_list())

        # Calculate the current number of running processes at this moment
        total_running_proc = 0
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['status'])
            if pinfo['status'] not in (psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD, psutil.STATUS_STOPPED):
                total_running_proc += 1
        self._running_process_count = total_running_proc

    def _get_local_mount_data(self):
        """Retrieves node information for the local_mount_data json message"""
        self._total_space = psutil.disk_usage("/")[0]/self._units_factor
        self._free_space  = psutil.disk_usage("/")[2]/self._units_factor
        self._total_swap  = psutil.swap_memory()[0]/self._units_factor
        self._free_swap   = psutil.swap_memory()[2]/self._units_factor
        self._free_inodes = int(100 - math.ceil((float(os.statvfs("/").f_files - os.statvfs("/").f_ffree) \
                             / os.statvfs("/").f_files) * 100))

    def _get_cpu_data(self):
        """Retrieves node information for the cpu_data json message"""
        cpu_data = psutil.cpu_times_percent()
        self._log_debug("_get_cpu_data, cpu_data: %s %s %s %s %s %s %s %s %s %s" % cpu_data)

        self._csps           = 0  # What the hell is csps - cycles per second?
        self._user_time      = int(cpu_data[0])
        self._nice_time      = int(cpu_data[1])
        self._system_time    = int(cpu_data[2])
        self._idle_time      = int(cpu_data[3])
        self._iowait_time    = int(cpu_data[4])
        self._interrupt_time = int(cpu_data[5])
        self._softirq_time   = int(cpu_data[6])
        self._steal_time     = int(cpu_data[7])

        # Array to hold data about each CPU core
        self._cpu_core_data = []
        index = 0
        while index < self._cpus:
            self._log_debug("_get_cpu_data, index: %s, 1 min: %s, 5 min: %s, 15 min: %s" %
                            (index,
                            self._load_1min_average[index],
                            self._load_5min_average[index],
                            self._load_15min_average[index]))

            cpu_core_data = {"coreId"      : index,
                             "load1MinAvg" : int(self._load_1min_average[index]),
                             "load5MinAvg" : int(self._load_5min_average[index]),
                             "load15MinAvg": int(self._load_15min_average[index]),
                             "ips" : 0
                             }
            self._cpu_core_data.append(cpu_core_data)
            index += 1

    def _get_if_data(self):
        """Retrieves node information for the if_data json message"""
        net_data = psutil.net_io_counters(pernic=True)

        # Array to hold data about each network interface
        self._if_data = []
        for interface, if_data in net_data.iteritems():
            self._log_debug("_get_if_data, interface: %s %s" % (interface, net_data))

            if_data = {"ifId" : interface,
                       "networkErrors"      : (net_data[interface].errin +
                                               net_data[interface].errout),
                       "droppedPacketsIn"   : net_data[interface].dropin,
                       "packetsIn"          : net_data[interface].packets_recv,
                       "trafficIn"          : net_data[interface].bytes_recv,
                       "droppedPacketsOut"  : net_data[interface].dropout,
                       "packetsOut"         : net_data[interface].packets_sent,
                       "trafficOut"         : net_data[interface].bytes_sent
                       }
            self._if_data.append(if_data)

    def _load_1min_avg(self):
        """Loop forever calculating the one minute average load"""
        # Initialize list to -1 indicating the time interval has not occurred yet
        index = 0
        while index < self._cpus:
            self._load_1min_average.append(-1)
            index += 1

        while True:
            # API call blocks for one minute and then returns the value
            self._load_1min_average = psutil.cpu_percent(interval=1, percpu=True)

    def _load_5min_avg(self):
        """Loop forever calculating the five minute average load"""
        # Initialize list to -1 indicating the time interval has not occurred yet
        index = 0
        while index < self._cpus:
            self._load_5min_average.append(-1)
            index += 1

        while True:
            # API call blocks for five minutes and then returns the value
            self._load_5min_average = psutil.cpu_percent(interval=5, percpu=True)

    def _load_15min_avg(self):
        """Loop forever calculating the fifteen minute average load"""
        # Initialize list to -1 indicating the time interval has not occurred yet
        index = 0
        while index < self._cpus:
            self._load_15min_average.append(-1)
            index += 1

        while True:
            # API call blocks for fifteen minutes and then returns the value
            self._load_15min_average = psutil.cpu_percent(interval=15, percpu=True)


    # General getters/setters below here
    def get_if_data(self):
        return self._if_data

    def get_csps(self):
        return self._csps

    def get_user_time(self):
        return self._user_time

    def get_nice_time(self):
        return self._nice_time

    def get_system_time(self):
        return self._system_time

    def get_idle_time(self):
        return self._idle_time

    def get_iowait_time(self):
        return self._iowait_time

    def get_interrupt_time(self):
        return self._interrupt_time

    def get_softirq_time(self):
        return self._softirq_time

    def get_steal_time(self):
        return self._steal_time

    def get_cpu_core_data(self):
        return self._cpu_core_data

    def get_host_id(self):
        return self._host_id

    def get_local_time(self):
        return self._local_time

    def get_boot_time(self):
        return self._boot_time

    def get_up_time(self):
        return self._up_time

    def get_uname(self):
        return self._uname

    def get_free_mem(self):
        return self._free_mem

    def get_free_mem_units(self):
        return self._free_mem_units

    def get_total_mem(self):
        return self._total_mem

    def get_total_mem_units(self):
        return self._total_mem_units

    def get_process_count(self):
        return self._process_count

    def get_running_process_count(self):
        return self._running_process_count

    def get_total_space(self):
        return self._total_space

    def get_total_swap(self):
        return self._total_swap  

    def get_free_space(self):
        return self._free_space

    def get_free_swap(self):
        return self._free_swap

    def get_inodes(self):
        return self._free_inodes