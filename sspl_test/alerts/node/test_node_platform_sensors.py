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

from common import check_sspl_ll_is_running, get_fru_response, send_node_controller_message_request
from framework.utils.conf_utils import Conf, SSPL_TEST_CONF, NODE_ID_KEY
from framework.base.sspl_constants import DEFAULT_NODE_ID


UUID="16476007-a739-4785-b5c6-f3de189cdf18"

def init(args):
    pass

def test_node_temperature_sensor(agrs):
    check_sspl_ll_is_running()
    instance_id = "*"
    resource_type = "node:sensor:temperature"
    target_node_id = Conf.get(SSPL_TEST_CONF, NODE_ID_KEY, DEFAULT_NODE_ID)
    send_node_controller_message_request(UUID, "NDHW:%s" % resource_type, instance_id, target_node_id)
    ingressMsg = get_fru_response(resource_type, instance_id)

    assert(ingressMsg.get("sspl_ll_msg_header").get("uuid") == UUID)
    sensor_msg = ingressMsg.get("actuator_response_type")
    assert(sensor_msg is not None)
    assert(sensor_msg.get("alert_type") is not None)
    assert(sensor_msg.get("severity") is not None)
    assert(sensor_msg.get("host_id") is not None)
    assert(sensor_msg.get("info") is not None)
    assert(sensor_msg.get("instance_id") == instance_id)

    temp_module_info = sensor_msg.get("info")
    assert(temp_module_info.get("site_id") is not None)
    assert(temp_module_info.get("node_id") is not None)
    assert(temp_module_info.get("rack_id") is not None)
    assert(temp_module_info.get("resource_type") is not None)
    assert(temp_module_info.get("event_time") is not None)
    assert(temp_module_info.get("resource_id") is not None)

    fru_specific_infos = sensor_msg.get("specific_info")
    assert(fru_specific_infos is not None)

    for fru_specific_info in fru_specific_infos:
        assert(fru_specific_info is not None)
        if fru_specific_info.get("ERROR"):
            # Skip any validation on specific info if ERROR seen on FRU
            continue
        assert(fru_specific_info.get("resource_id") is not None)
        resource_id = fru_specific_info.get("resource_id")
        if fru_specific_info.get(resource_id):
            assert(fru_specific_info.get(resource_id).get("ERROR") is not None)
            # Skip any validation on specific info if ERROR seen on sensor
            continue
        assert(fru_specific_info.get("sensor_number") is not None)
        assert(fru_specific_info.get("sensor_status") is not None)
        assert(fru_specific_info.get("entity_id_instance") is not None)
        assert(fru_specific_info.get("sensor_reading") is not None)


def test_node_voltage_sensor(agrs):
    check_sspl_ll_is_running()
    instance_id = "*"
    resource_type = "node:sensor:voltage"
    target_node_id = Conf.get(SSPL_TEST_CONF, NODE_ID_KEY, DEFAULT_NODE_ID)
    send_node_controller_message_request(UUID, "NDHW:%s" % resource_type, instance_id, target_node_id)
    ingressMsg = get_fru_response(resource_type, instance_id)

    assert(ingressMsg.get("sspl_ll_msg_header").get("uuid") == UUID)
    sensor_msg = ingressMsg.get("actuator_response_type")
    assert(sensor_msg is not None)
    assert(sensor_msg.get("alert_type") is not None)
    assert(sensor_msg.get("severity") is not None)
    assert(sensor_msg.get("host_id") is not None)
    assert(sensor_msg.get("info") is not None)
    assert(sensor_msg.get("instance_id") == instance_id)

    volt_module_info = sensor_msg.get("info")
    assert(volt_module_info.get("site_id") is not None)
    assert(volt_module_info.get("node_id") is not None)
    assert(volt_module_info.get("rack_id") is not None)
    assert(volt_module_info.get("resource_type") is not None)
    assert(volt_module_info.get("event_time") is not None)
    assert(volt_module_info.get("resource_id") is not None)

    fru_specific_infos = sensor_msg.get("specific_info")
    assert(fru_specific_infos is not None)

    for fru_specific_info in fru_specific_infos:
        assert(fru_specific_info is not None)
        if fru_specific_info.get("ERROR"):
            # Skip any validation on specific info if ERROR seen on FRU
            continue
        assert(fru_specific_info.get("resource_id") is not None)
        resource_id = fru_specific_info.get("resource_id")
        if fru_specific_info.get(resource_id):
            assert(fru_specific_info.get(resource_id).get("ERROR") is not None)
            # Skip any validation on specific info if ERROR seen on sensor
            continue
        assert(fru_specific_info.get("sensor_number") is not None)
        assert(fru_specific_info.get("sensor_status") is not None)
        assert(fru_specific_info.get("entity_id_instance") is not None)
        assert(fru_specific_info.get("sensor_reading") is not None)


test_list = [
    test_node_temperature_sensor,
    test_node_voltage_sensor
    ]

