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

from framework.base.functional_test_base import TestCaseBase
from common import actuator_response_filter, get_enclosure_request


class RealStorDiskActuatorTest(TestCaseBase):
    resource_type = "enclosure:hw:disk"
    resource_id = "*"

    def init(self):
        pass

    def request(self):
        return get_enclosure_request("ENCL:%s" % self.resource_type, self.resource_id)

    def filter(self, msg):
        return actuator_response_filter(msg, self.resource_type)

    def response(self, msg):
        disk_actuator_msg = msg.get("actuator_response_type")

        assert(disk_actuator_msg is not None)
        assert(disk_actuator_msg.get("alert_type") is not None)
        assert(disk_actuator_msg.get("alert_id") is not None)
        assert(disk_actuator_msg.get("severity") is not None)
        assert(disk_actuator_msg.get("host_id") is not None)
        assert(disk_actuator_msg.get("info") is not None)

        disk_actuator_info = disk_actuator_msg.get("info")
        assert(disk_actuator_info.get("site_id") is not None)
        assert(disk_actuator_info.get("node_id") is not None)
        assert(disk_actuator_info.get("cluster_id") is not None)
        assert(disk_actuator_info.get("rack_id") is not None)
        assert(disk_actuator_info.get("resource_type") is not None)
        assert(disk_actuator_info.get("event_time") is not None)
        assert(disk_actuator_info.get("resource_id") is not None)

        disk_actuator_specific_infos = disk_actuator_msg.get("specific_info")
        for disk_actuator_specific_info in disk_actuator_specific_infos:
            assert(disk_actuator_specific_info is not None)
            assert(disk_actuator_specific_info.get("description") is not None)
            assert(disk_actuator_specific_info.get("slot") is not None)
            assert(disk_actuator_specific_info.get("status") is not None)
            assert(disk_actuator_specific_info.get("architecture") is not None)
            assert(disk_actuator_specific_info.get("serial_number") is not None)
            assert(disk_actuator_specific_info.get("size") is not None)
            assert(disk_actuator_specific_info.get("vendor") is not None)
            assert(disk_actuator_specific_info.get("model") is not None)
            assert(disk_actuator_specific_info.get("revision") is not None)
            assert(disk_actuator_specific_info.get("temperature") is not None)
            assert(disk_actuator_specific_info.get("LED_status".lower()) is not None)
            assert(disk_actuator_specific_info.get("locator_LED".lower()) is not None)
            assert(disk_actuator_specific_info.get("blink") is not None)
            assert(disk_actuator_specific_info.get("smart") is not None)
            assert(disk_actuator_specific_info.get("health") is not None)
            assert(disk_actuator_specific_info.get("health_reason") is not None)
            assert(disk_actuator_specific_info.get("health_recommendation") is not None)
            assert(disk_actuator_specific_info.get("enclosure_id") is not None)
            assert(disk_actuator_specific_info.get("enclosure_wwn") is not None)


test_list = [RealStorDiskActuatorTest]
