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

# -*- coding: utf-8 -*-

from common import check_sspl_ll_is_running, get_fru_response, send_enclosure_request


def init(args):
    pass

def test_real_stor_controller_actuator(agrs):
    instance_id = "*"
    resource_type = "enclosure:hw:controller"
    send_enclosure_request("ENCL:%s" % resource_type, instance_id)
    ingressMsg = get_fru_response(resource_type, instance_id)
    controller_actuator_msg = ingressMsg.get("actuator_response_type")

    assert(controller_actuator_msg is not None)
    assert(controller_actuator_msg.get("alert_type") is not None)
    assert(controller_actuator_msg.get("alert_id") is not None)
    assert(controller_actuator_msg.get("severity") is not None)
    assert(controller_actuator_msg.get("host_id") is not None)
    assert(controller_actuator_msg.get("info") is not None)
    assert(controller_actuator_msg.get("specific_info") is not None)

    info = controller_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_infos = controller_actuator_msg.get("specific_info")
    for specific_info in specific_infos:
        assert(specific_info.get("object_name") is not None)
        assert(specific_info.get("controller_id") is not None)
        assert(specific_info.get("serial_number") is not None)
        assert(specific_info.get("hardware_version") is not None)
        assert(specific_info.get("cpld_version") is not None)
        assert(specific_info.get("mac_address") is not None)
        assert(specific_info.get("node_wwn") is not None)
        assert(specific_info.get("ip_address") is not None)
        assert(specific_info.get("ip_subnet_mask") is not None)
        assert(specific_info.get("ip_gateway") is not None)
        assert(specific_info.get("disks") is not None)
        assert(specific_info.get("number_of_storage_pools") is not None)
        assert(specific_info.get("virtual_disks") is not None)
        assert(specific_info.get("host_ports") is not None)
        assert(specific_info.get("drive_channels") is not None)
        assert(specific_info.get("drive_bus_type") is not None)
        assert(specific_info.get("status") is not None)
        assert(specific_info.get("failed_over") is not None)
        assert(specific_info.get("fail_over_reason") is not None)
        assert(specific_info.get("vendor") is not None)
        assert(specific_info.get("model") is not None)
        assert(specific_info.get("platform_type") is not None)
        assert(specific_info.get("write_policy") is not None)
        assert(specific_info.get("description") is not None)
        assert(specific_info.get("part_number") is not None)
        assert(specific_info.get("revision") is not None)
        assert(specific_info.get("mfg_vendor_id") is not None)
        assert(specific_info.get("locator_led") is not None)
        assert(specific_info.get("health") is not None)
        assert(specific_info.get("health_reason") is not None)
        assert(specific_info.get("position") is not None)
        assert(specific_info.get("redundancy_mode") is not None)
        assert(specific_info.get("redundancy_status") is not None)
        assert(specific_info.get("compact_flash") is not None)
        assert(specific_info.get("network_parameters") is not None)
        assert(specific_info.get("expander_ports") is not None)
        assert(specific_info.get("expanders") is not None)
        assert(specific_info.get("port") is not None)


test_list = [test_real_stor_controller_actuator]
