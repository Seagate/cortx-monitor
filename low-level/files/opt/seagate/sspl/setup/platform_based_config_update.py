#!/usr/bin/python3.6

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

import os
import consul

# Using cortx package
from cortx.utils.conf_store import Conf


def update_sensor_info(config_index, node_type, enclosure_type):
    """Enable or disable sensor monitoring based on node_type
    and enclosure_type.
    """
    sensors = dict()
    sensors["REALSTORSENSORS"] = "true"
    sensors["NODEHWSENSOR"] = "true"
    sensors["DISKMONITOR"] = "true"
    sensors["SERVICEMONITOR"] = "true"
    sensors["RAIDSENSOR"] = "true"
    sensors["RAIDINTEGRITYSENSOR"] = "true"
    sensors["SASPORTSENSOR"] = "true"
    sensors["MEMFAULTSENSOR"] = "true"
    sensors["CPUFAULTSENSOR"] = "true"

    if enclosure_type and enclosure_type.lower() in ["virtual", "vm", "jbod"]:
        sensors["REALSTORSENSORS"] = "false"

    if node_type and node_type.lower() in ["virtual", "vm"]:
        sensors["NODEHWSENSOR"] = "false"
        sensors["SASPORTSENSOR"] = "false"
        sensors["MEMFAULTSENSOR"] = "false"
        sensors["CPUFAULTSENSOR"] = "false"
        sensors["RAIDSENSOR"] = "false"
        sensors["RAIDINTEGRITYSENSOR"] = "false"

    # Update sensor information in config
    for sect, value in sensors.items():
        Conf.set(config_index, '%s>monitor' % sect, value)

    Conf.save(config_index)

def update_monitored_services(config_index, node_type):
    """Based on node type exclude the services from list
    of monitored services.
    """
    # Align to node type as used in sspl.conf SERVICEMONITOR section
    vm_types = ["virtual", "vm"]
    node_type = "vm" if node_type.lower() in vm_types else "hw"

    monitored_services = Conf.get(
        config_index, "SERVICEMONITOR>monitored_services", [])
    excluded_services = Conf.get(
        config_index,
        "SERVICEMONITOR>excluded_services>%s" % node_type, [])

    # Have only required list of services to be monitored
    monitored_services = list(set(monitored_services) - set(excluded_services))
    Conf.set(
        config_index, "SERVICEMONITOR>monitored_services",
        monitored_services)
    Conf.save(config_index)
