# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com

from common import (check_sspl_ll_is_running, get_fru_response,
                    send_node_data_message_request)

UUID = "10000001-a739-4785-b5c6-f3de189abc01"


def init(args):
    pass


def test_node_hba_sensor(args):
    check_sspl_ll_is_running()
    resource_type = "node:hw:hba"
    send_node_data_message_request(UUID, resource_type)
    ingress_msg = get_fru_response(resource_type,
                                  ingress_msg_type="sensor_response_type")

    assert(ingress_msg.get("sspl_ll_msg_header").get("uuid") == UUID)

    hba_sensor_msg = ingress_msg.get("sensor_response_type")
    assert(hba_sensor_msg is not None)
    assert(hba_sensor_msg.get("alert_type") is not None)
    assert(hba_sensor_msg.get("severity") is not None)
    assert(hba_sensor_msg.get("host_id") is not None)
    assert(hba_sensor_msg.get("info") is not None)

    hba_info = hba_sensor_msg.get("info")
    assert(hba_info.get("site_id") is not None)
    assert(hba_info.get("node_id") is not None)
    assert(hba_info.get("rack_id") is not None)
    assert(hba_info.get("resource_type") == resource_type)
    assert(hba_info.get("event_time") is not None)
    assert(hba_info.get("resource_id") is not None)

    hba_specific_info = hba_sensor_msg.get("specific_info")
    assert(hba_specific_info is not None)
    if hba_specific_info.get("initiators_count"):
        assert(hba_specific_info.get("host_type") is not None)


test_list = [test_node_hba_sensor]
