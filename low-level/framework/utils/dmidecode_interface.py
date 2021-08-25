# Copyright (c) 2019-2020 Seagate Technology LLC and/or its Affiliates
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
import psutil
import traceback
from statistics import mean
from framework.utils.utility import Utility
from framework.utils.service_logging import logger
from cortx.utils.process import SimpleProcess


class Dmidecode(Utility):
    """
    Interface class to retrieve system's hardware related information
    using 'dmidecode' command.

    """
    DMIDECODE = "sudo /sbin/dmidecode"

    def __init__(self):
        """Init method."""
        super(Dmidecode, self).__init__()

    def get_cpu_info(self):
        """Returns a dict having CPU information.

        For example:
            output of resulted CPU dict -
            {'cpu_present': [0, 1],
            'online_cpus': [0, 1],
            'cpu_usage': [0.59, 0.56]
            }

        """
        try:
            cmd = self.DMIDECODE + " -t 4"
            response, err, _ = SimpleProcess(cmd).run()
            if err:
                logger.error("Failed to get list of Online CPUs."
                             f"ERROR:{err}")
                return
            matches = re.findall("Socket Designation:.*|"
                                 "Status:.*|"
                                 "Thread Count:.*", response.decode())

            cpu_status_map = {}
            cpu_thread_map = {}
            cpu_list = []
            cpu_present = cpu_status = cpu_threads = None
            while matches:
                item = matches.pop(0)
                if "Designation:" in item:
                    cpu_str = item.strip().split(": ")[1]
                    cpu_dig = re.findall(r'\d+', cpu_str)
                    cpu_present = cpu_dig.pop(0)
                    cpu_list.append(int(cpu_present))
                if "Status:" in item:
                    cpu_status = item.strip().split(": ")[1]
                if "Thread Count:" in item:
                    cpu_threads = item.strip().split(": ")[1]
                if cpu_status:
                    cpu_status_map[cpu_present] = cpu_status
                if cpu_threads:
                    cpu_thread_map[cpu_present] = cpu_threads

            online_cpus = []
            per_cpu_usage = []
            cpu_info = {}
            for cpu, status in cpu_status_map.items():
                if "Enabled" in status:
                    online_cpus.append(int(cpu))

            # psutil gives cpu_usage per thread, taking mean value of threads
            # available per cpu to calculate per_cpu_usage
            cpu_usage_threads = psutil.cpu_percent(interval=None, percpu=True)
            for _, threads in cpu_thread_map.items():
                thread_avg = cpu_usage_threads[:int(threads)]
                cpu_usage_threads = cpu_usage_threads[int(threads):]
                usage = mean(thread_avg)
                cpu_usage = round(usage, 2)
                per_cpu_usage.append(cpu_usage)

            cpu_info["cpu_present"] = cpu_list
            cpu_info["online_cpus"] = online_cpus
            cpu_info["cpu_usage"] = per_cpu_usage
            logger.info(f"Fetched CPU info: {cpu_info}")
            return cpu_info
        except Exception as e:
            logger.error(f"Failed to get CPUs info. ERROR:{e}")
            logger.debug("%s\n" % traceback.format_exc())
            return
