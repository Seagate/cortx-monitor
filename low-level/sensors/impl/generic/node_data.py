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

        self.host_id = None

        # Total number of CPUs
        self.cpus = psutil.cpu_count()

        # Calculate the load averages on separate blocking threads
        self.load_1min_average  = []
        self.load_5min_average  = []
        self.load_15min_average = []
        load_1min_avg  = os.getloadavg()[0]
        load_5min_avg  = os.getloadavg()[1]
        load_15min_avg = os.getloadavg()[2]

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
            if socket.gethostname().find('.') >= 0:
                self.host_id = socket.gethostname()
            else:
                self.host_id = socket.gethostbyaddr(socket.gethostname())[0]

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

        except Exception as e:
            logger.exception(e)
            return False

        return True

    def _get_host_update_data(self):
        """Retrieves node information for the host_update json message"""
        self.up_time         = int(psutil.boot_time())
        self.boot_time       = datetime.fromtimestamp(self.up_time).strftime('%Y-%m-%d %H:%M:%S %Z')
        self.uname           = ' '.join(os.uname())
        self.free_mem        = int(psutil.virtual_memory()[1])/self.units_factor
        self.total_mem       = int(psutil.virtual_memory()[0])/self.units_factor
        self.process_count   = len(psutil.get_pid_list())

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
        self.total_space = psutil.disk_usage("/")[0]/self.units_factor
        self.free_space  = psutil.disk_usage("/")[2]/self.units_factor
        self.total_swap  = psutil.swap_memory()[0]/self.units_factor
        self.free_swap   = psutil.swap_memory()[2]/self.units_factor
        self.free_inodes = int(100 - math.ceil((float(os.statvfs("/").f_files - os.statvfs("/").f_ffree) \
                             / os.statvfs("/").f_files) * 100))

    def _get_cpu_data(self):
        """Retrieves node information for the cpu_data json message"""
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
            self.if_data.append(if_data)

