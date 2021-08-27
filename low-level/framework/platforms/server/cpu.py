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

import re
import psutil
import traceback
from statistics import mean

from framework.utils.system_info import SystemInfo
from framework.utils.service_logging import logger

class CPU:

    @staticmethod
    def get_cpu_info():
        """Returns a dict having CPU information.

        For example:
            output of resulted CPU dict -
            {'cpu_present': [0, 1],
            'online_cpus': [0, 1],
            'cpu_usage': [0.59, 0.56]
            }

        """
        try:
            response, err, _ = SystemInfo().get_system_info("cpu")
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
            while matches:
                item = matches.pop(0)
                if "Designation:" in item:
                    cpu_str = item.strip().split(": ")[1]
                    cpu_dig = re.findall(r'\d+', cpu_str)
                    cpu_present = cpu_dig.pop(0)
                    cpu_list.append(int(cpu_present))
                if "Status:" in item:
                    cpu_status = item.strip().split(": ")[1]
                    cpu_status_map[cpu_present] = cpu_status if cpu_status else None
                if "Thread Count:" in item:
                    cpu_threads = item.strip().split(": ")[1]
                    cpu_thread_map[cpu_present] = cpu_threads if cpu_threads else None

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
            logger.debug(f"Fetched CPU info: {cpu_info}")
            return cpu_info
        except Exception as e:
            logger.error(f"Failed to get CPUs info. ERROR:{e}")
            logger.debug("%s\n" % traceback.format_exc())
            return