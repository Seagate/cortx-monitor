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

from framework.base.functional_test_base import TestCaseBase
from common import actuator_response_filter, get_node_controller_message_request


class NodePsuActuatorTest(TestCaseBase):
    resource_type = "node:hw:psu"
    resource_id = "*"
    UUID = "16476007-a739-4785-b5c6-f3de189cdf12"

    def init(self):
        pass

    def request(self):
        return get_node_controller_message_request(self.UUID, "NDHW:%s" % self.resource_type, self.resource_id)

    def filter(self, msg):
        return actuator_response_filter(msg, self.resource_type)

    def response(self, msg):
        assert(msg.get("sspl_ll_msg_header").get("uuid") == self.UUID)

        psu_module_actuator_msg = msg.get("actuator_response_type")
        assert(psu_module_actuator_msg is not None)
        assert(psu_module_actuator_msg.get("alert_type") is not None)
        assert(psu_module_actuator_msg.get("severity") is not None)
        assert(psu_module_actuator_msg.get("host_id") is not None)
        assert(psu_module_actuator_msg.get("info") is not None)
        assert(psu_module_actuator_msg.get("instance_id") == self.resource_id)

        psu_module_info = psu_module_actuator_msg.get("info")
        assert(psu_module_info.get("site_id") is not None)
        assert(psu_module_info.get("node_id") is not None)
        assert(psu_module_info.get("rack_id") is not None)
        assert(psu_module_info.get("resource_type") is not None)
        assert(psu_module_info.get("event_time") is not None)
        assert(psu_module_info.get("resource_id") is not None)

        fru_specific_infos = psu_module_actuator_msg.get("specific_info")
        assert(fru_specific_infos is not None)

        if psu_module_actuator_msg.get("instance_id") == "*":
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
                assert(fru_specific_info.get("States Asserted") is not None)
                sensor_type = [
                    k if k.startswith("Sensor Type") else None
                    for k in fru_specific_info.keys()
                    ][0]
                assert(sensor_type is not None)
        else:
            # Skip any validation if ERROR seen on the specifc FRU
            if not fru_specific_infos.get("ERROR"):
                assert(fru_specific_infos.get("States Asserted") is not None)
                sensor_type = [
                    k if k.startswith("Sensor Type") else None
                    for k in fru_specific_infos.keys()
                    ][0]
                assert(sensor_type is not None)


test_list = [NodePsuActuatorTest]
