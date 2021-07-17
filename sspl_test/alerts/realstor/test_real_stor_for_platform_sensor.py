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
    check_sspl_ll_is_running, get_fru_response, send_enclosure_actuator_request)


def init(args):
    pass


def test_real_stor_sensor_current(args):
    instance_id = "*"
    resource_type = "storage:hw:platform_sensor:current"
    ingress_msg_type = "actuator_response_type"
    send_enclosure_actuator_request("ENCL:%s" % resource_type, instance_id)
    ingressMsg = get_fru_response(
        resource_type, instance_id, ingress_msg_type)
    current_module_actuator_msg = ingressMsg.get(ingress_msg_type)

    assert(current_module_actuator_msg is not None)
    assert(current_module_actuator_msg.get("alert_type") is not None)
    assert(current_module_actuator_msg.get("alert_id") is not None)
    assert(current_module_actuator_msg.get("severity") is not None)
    assert(current_module_actuator_msg.get("host_id") is not None)
    assert(current_module_actuator_msg.get("info") is not None)
    assert(current_module_actuator_msg.get("specific_info") is not None)

    info = current_module_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = current_module_actuator_msg.get("specific_info")
    generic_specific_info(specific_info)


def test_real_stor_sensor_voltage(agrs):
    instance_id = "*"
    resource_type = "storage:hw:platform_sensor:voltage"
    ingress_msg_type = "actuator_response_type"
    send_enclosure_actuator_request("ENCL:%s" % resource_type, instance_id)
    ingressMsg = get_fru_response(
        resource_type, instance_id, ingress_msg_type)
    voltage_module_actuator_msg = ingressMsg.get(ingress_msg_type)

    assert(voltage_module_actuator_msg is not None)
    assert(voltage_module_actuator_msg.get("alert_type") is not None)
    assert(voltage_module_actuator_msg.get("alert_id") is not None)
    assert(voltage_module_actuator_msg.get("severity") is not None)
    assert(voltage_module_actuator_msg.get("host_id") is not None)
    assert(voltage_module_actuator_msg.get("info") is not None)
    assert(voltage_module_actuator_msg.get("specific_info") is not None)

    info = voltage_module_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = voltage_module_actuator_msg.get("specific_info")
    generic_specific_info(specific_info)


def test_real_stor_sensor_temperature(agrs):
    instance_id = "*"
    resource_type = "storage:hw:platform_sensor:temperature"
    ingress_msg_type = "actuator_response_type"
    send_enclosure_actuator_request("ENCL:%s" % resource_type, instance_id)
    ingressMsg = get_fru_response(
        resource_type, instance_id, ingress_msg_type)
    temperature_module_actuator_msg = ingressMsg.get(ingress_msg_type)

    assert(temperature_module_actuator_msg is not None)
    assert(temperature_module_actuator_msg.get("alert_type") is not None)
    assert(temperature_module_actuator_msg.get("alert_id") is not None)
    assert(temperature_module_actuator_msg.get("severity") is not None)
    assert(temperature_module_actuator_msg.get("host_id") is not None)
    assert(temperature_module_actuator_msg.get("info") is not None)
    assert(temperature_module_actuator_msg.get("specific_info") is not None)

    info = temperature_module_actuator_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = temperature_module_actuator_msg.get("specific_info")
    generic_specific_info(specific_info)


def generic_specific_info(specific_info):
    for resource in specific_info:
        assert(resource.get("drawer_id_numeric") is not None)
        assert(resource.get("sensor_type") is not None)
        assert(resource.get("container") is not None)
        assert(resource.get("enclosure_id") is not None)
        assert(resource.get("durable_id") is not None)
        assert(resource.get("value") is not None)
        assert(resource.get("status") is not None)
        assert(resource.get("controller_id_numeric") is not None)
        assert(resource.get("object_name") is not None)
        assert(resource.get("container_numeric") is not None)
        assert(resource.get("controller_id") is not None)
        assert(resource.get("sensor_type_numeric") is not None)
        assert(resource.get("sensor_name") is not None)
        assert(resource.get("drawer_id") is not None)
        assert(resource.get("status_numeric") is not None)


test_list = [test_real_stor_sensor_current, test_real_stor_sensor_voltage, test_real_stor_sensor_temperature]
