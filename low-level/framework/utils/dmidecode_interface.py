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

"""
Module which provides system information using 'dmidecode' command
"""

import re

from pathlib import Path
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
        """init method"""
        super(Dmidecode, self).__init__()

    def get_cpu_info(self):
        """Returns online cpus list"""
        try:
            cmd = self.DMIDECODE + " -t 4"
            response, err, _ = SimpleProcess(cmd).run()
            if err:
                logger.error("Failed to get list of Online CPUs."
                             f"ERROR:{err}")
                return
            matches = re.findall("Socket Designation:.*|"
                                 "Status:.*", response.decode())
    
            cpu_map = {}
            cpu = cpu_status = None
            while matches:
                item = matches.pop(0)
                if "Designation:" in item:
                    cpu = item.strip().split(": ")[1]
                if "Status:" in item:
                    cpu_status = item.strip().split(": ")[1]
                if cpu and cpu_status:
                    cpu_map[cpu] = cpu_status
            logger.debug(f"Mapping of CPU and status:{cpu_map}")
            online_cpus = []
            for cpu, status in cpu_map.items():
                if "Enabled" in status:
                    online_cpus.append(cpu)
            logger.info(f"Online CPU list:{online_cpus}")
            return online_cpus
        except Exception as e:
            logger.error(f"Failed to get online CPUs info. ERROR:{e}")

