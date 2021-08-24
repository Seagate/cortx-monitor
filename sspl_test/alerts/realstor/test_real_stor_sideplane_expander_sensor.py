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
from common import (
    check_sspl_ll_is_running, get_fru_response, send_enclosure_sensor_request)


def init(args):
    pass

def test_real_stor_sideplane_expander_sensor(args):
    check_sspl_ll_is_running()
    instance_id = "*"
    resource_type = "storage:hw:sideplane"
    ingress_msg_type = "sensor_response_type"
    send_enclosure_sensor_request(resource_type, instance_id)
    ingressMsg = get_fru_response(
        resource_type, instance_id, ingress_msg_type)
    sideplane_expander_sensor_msg = ingressMsg.get(ingress_msg_type)

    assert(sideplane_expander_sensor_msg is not None)
    assert(sideplane_expander_sensor_msg.get("alert_type") is not None)
    assert(sideplane_expander_sensor_msg.get("alert_id") is not None)
    assert(sideplane_expander_sensor_msg.get("host_id") is not None)
    assert(sideplane_expander_sensor_msg.get("severity") is not None)
    assert(sideplane_expander_sensor_msg.get("info") is not None)

    sideplane_expander_info_data = sideplane_expander_sensor_msg.get("info")
    assert(sideplane_expander_info_data.get("site_id") is not None)
    assert(sideplane_expander_info_data.get("node_id") is not None)
    assert(sideplane_expander_info_data.get("cluster_id") is not None)
    assert(sideplane_expander_info_data.get("rack_id") is not None)
    assert(sideplane_expander_info_data.get("resource_type") is not None)
    assert(sideplane_expander_info_data.get("event_time") is not None)
    assert(sideplane_expander_info_data.get("resource_id") is not None)
    assert(sideplane_expander_info_data.get("description") is not None)

    sideplane_expander_specific_info_data = sideplane_expander_sensor_msg.get("specific_info", {})

    if sideplane_expander_specific_info_data:
        assert(sideplane_expander_specific_info_data.get("position") is not None)
        assert(sideplane_expander_specific_info_data.get("durable_id") is not None)
        assert(sideplane_expander_specific_info_data.get("drawer_id") is not None)
        assert(sideplane_expander_specific_info_data.get("status") is not None)
        assert(sideplane_expander_specific_info_data.get("name") is not None)
        assert(sideplane_expander_specific_info_data.get("enclosure_id") is not None)
        assert(sideplane_expander_specific_info_data.get("health_reason") is not None)
        assert(sideplane_expander_specific_info_data.get("health") is not None)
        assert(sideplane_expander_specific_info_data.get("location") is not None)
        assert(sideplane_expander_specific_info_data.get("health_recommendation") is not None)


test_list = [test_real_stor_sideplane_expander_sensor]
