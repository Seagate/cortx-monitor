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

from framework.base.testcase_base import TestCaseBase
from common import actuator_response_filter


class SystemdServiceValidRequestTest(TestCaseBase):
    resource_type = "node:sw:os:service"
    action = "status"
    service_name = "rsyslog.service"

    def init(self):
        pass

    def request(self):
        return service_actuator_request(self.service_name, self.action)

    def filter(self, msg):
        return actuator_response_filter(msg, self.resource_type, self.service_name)

    def response(self, msg):
        service_actuator_msg = msg.get("actuator_response_type")

        assert(service_actuator_msg is not None)
        assert(service_actuator_msg.get("alert_type") == "UPDATE")
        assert(service_actuator_msg.get("severity") is not None)
        assert(service_actuator_msg.get("host_id") is not None)
        assert(service_actuator_msg.get("info") is not None)

        info = service_actuator_msg.get("info")
        assert(info.get("site_id") is not None)
        assert(info.get("node_id") is not None)
        assert(info.get("cluster_id") is not None)
        assert(info.get("rack_id") is not None)
        assert(info.get("resource_type") == self.resource_type)
        assert(info.get("event_time") is not None)
        assert(info.get("resource_id") == self.service_name)
        assert(service_actuator_msg.get("specific_info") is not None)


class SystemdServiceInvalidRequestTest(TestCaseBase):
    resource_type = "node:sw:os:service"
    action = "start"
    service_name = "temp_dummy.service"

    def init(self):
        pass

    def request(self):
        return service_actuator_request(self.service_name, self.action)

    def filter(self, msg):
        return actuator_response_filter(msg, self.resource_type, self.service_name)

    def response(self, msg):
        service_actuator_msg = msg.get("actuator_response_type")

        assert(service_actuator_msg is not None)
        assert(service_actuator_msg.get("alert_type") == "UPDATE")
        assert(service_actuator_msg.get("severity") is not None)
        assert(service_actuator_msg.get("host_id") is not None)
        assert(service_actuator_msg.get("info") is not None)

        info = service_actuator_msg.get("info")
        assert(info.get("site_id") is not None)
        assert(info.get("node_id") is not None)
        assert(info.get("cluster_id") is not None)
        assert(info.get("rack_id") is not None)
        assert(info.get("resource_type") == self.resource_type)
        assert(info.get("event_time") is not None)
        assert(info.get("resource_id") == self.service_name)

        assert(service_actuator_msg.get("specific_info") is not None)
        specific_info = service_actuator_msg.get("specific_info")
        assert (specific_info[0].get("error_msg") is not None)


def service_actuator_request(service_name, action):
    egressMsg = {
                "title": "SSPL-LL Actuator Request",
                "description": "Seagate Storage Platform Library - Actuator Request",
                "username": "sspl-ll",
                "expires": 3600,
                "signature": "None",
                "time": "2020-03-06 04:08:04.071170",
                "message": {
                    "sspl_ll_debug": {
                        "debug_component": "sensor",
                        "debug_enabled": True
                    },
                    "sspl_ll_msg_header": {
                        "msg_version": "1.0.0",
                        "uuid": "9e6b8e53-10f7-4de0-a9aa-b7895bab7774",
                        "schema_version": "1.0.0",
                        "sspl_version": "2.0.0"
                    },
                    "request_path": {
                        "site_id": "1",
                        "rack_id": "1",
                        "node_id": "1"
                    },
                    "response_dest": {},
                    "actuator_request_type": {
                        "service_controller": {
                            "service_request": action,
                            "service_name": service_name
                        }
                    }
                }
            }
    return egressMsg


test_list = [SystemdServiceValidRequestTest, SystemdServiceInvalidRequestTest]
