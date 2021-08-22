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
from common import sensor_response_filter


class RealStorSideplaneExpanderSensorTest(TestCaseBase):
    resource_type = "enclosure:hw:sideplane"

    def init(self):
        pass

    def filter(self, msg):
        return sensor_response_filter(msg, self.resource_type)

    def request(self):
        return self.sideplane_expander_sensor_message_request()

    def response(self, msg):
        sideplane_expander_sensor_msg = msg.get("sensor_response_type")

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


    def sideplane_expander_sensor_message_request(self):
        egressMsg = {
            "title": "SSPL Actuator Request",
            "description": "Seagate Storage Platform Library - Actuator Request",

            "username": "JohnDoe",
            "signature": "None",
            "time": "2015-05-29 14:28:30.974749",
            "expires": 500,

            "message": {
                "sspl_ll_msg_header": {
                    "schema_version": "1.0.0",
                    "sspl_version": "1.0.0",
                    "msg_version": "1.0.0"
                },
                "sspl_ll_debug": {
                    "debug_component": "sensor",
                    "debug_enabled": True
                },
                "sensor_request_type": {
                    "enclosure_alert": {
                        "info": {
                            "resource_type": self.resource_type
                        }
                    }
                }
            }
        }
        return egressMsg


test_list = [RealStorSideplaneExpanderSensorTest]
