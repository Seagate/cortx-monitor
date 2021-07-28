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
from framework.utils.conf_utils import Conf, SSPL_TEST_CONF, NODE_ID_KEY
from framework.base.sspl_constants import DEFAULT_NODE_ID


def init(args):
    pass

def test_real_stor_psu_actuator(agrs):
    instance_id = "*"
    resource_type = "enclosure:fru:psu"
    target_node_id = Conf.get(SSPL_TEST_CONF, NODE_ID_KEY, DEFAULT_NODE_ID)
    send_enclosure_request("ENCL:%s" % resource_type, instance_id, target_node_id)
    ingressMsg = get_fru_response(resource_type, instance_id)
    psu_actuator_msg = ingressMsg.get("actuator_response_type")

    assert(psu_actuator_msg is not None)
    assert(psu_actuator_msg.get("host_id") is not None)
    assert(psu_actuator_msg.get("alert_type") is not None)
    assert(psu_actuator_msg.get("severity") is not None)
    assert(psu_actuator_msg.get("alert_id") is not None)
    psu_info = psu_actuator_msg.get("info")
    assert(psu_info is not None)
    assert(psu_info.get("site_id") is not None)
    assert(psu_info.get("cluster_id") is not None)
    assert(psu_info.get("rack_id") is not None)
    assert(psu_info.get("node_id") is not None)
    assert(psu_info.get("resource_type") is not None)
    assert(psu_info.get("resource_id") is not None)
    assert(psu_info.get("event_time") is not None)

    psu_actuator_specific_info_array = psu_actuator_msg.get("specific_info")
    for psu_specific_info in psu_actuator_specific_info_array:
        assert(psu_specific_info is not None)
        assert(psu_specific_info.get("dctemp") is not None)
        assert(psu_specific_info.get("dc33v") is not None)
        assert(psu_specific_info.get("fru_shortname") is not None)
        assert(psu_specific_info.get("health_reason") is not None)
        assert(psu_specific_info.get("serial_number") is not None)
        assert(psu_specific_info.get("mfg_date") is not None)
        assert(psu_specific_info.get("dash_level") is not None)
        assert(psu_specific_info.get("dom_id") is not None)
        assert(psu_specific_info.get("dc5i") is not None)
        assert(psu_specific_info.get("enclosure_id") is not None)
        assert(psu_specific_info.get("position_numeric") is not None)
        assert(psu_specific_info.get("durable_id") is not None)
        assert(psu_specific_info.get("configuration_serialnumber") is not None)
        assert(psu_specific_info.get("health") is not None)
        assert(psu_specific_info.get("location") is not None)
        assert(psu_specific_info.get("dc5v") is not None)
        assert(psu_specific_info.get("status_numeric") is not None)
        assert(psu_specific_info.get("revision") is not None)
        assert(psu_specific_info.get("mfg_location") is not None)
        assert(psu_specific_info.get("dc12v") is not None)
        assert(psu_specific_info.get("vendor") is not None)
        assert(psu_specific_info.get("description") is not None)
        assert(psu_specific_info.get("mfg_date_numeric") is not None)
        assert(psu_specific_info.get("object_name") is not None)
        assert(psu_specific_info.get("part_number") is not None)
        assert(psu_specific_info.get("health_recommendation") is not None)
        assert(psu_specific_info.get("health_numeric") is not None)
        assert(psu_specific_info.get("dc12i") is not None)
        assert(psu_specific_info.get("name") is not None)
        assert(psu_specific_info.get("fw_revision") is not None)
        assert(psu_specific_info.get("position") is not None)
        assert(psu_specific_info.get("model") is not None)
        assert(psu_specific_info.get("mfg_vendor_id") is not None)


test_list = [test_real_stor_psu_actuator]
