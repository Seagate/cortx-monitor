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

import os
import time
import uuid

from default import world
from common import (
    check_sspl_ll_is_running, get_fru_response, send_node_controller_message_request,
    get_current_node_id)
from framework.utils.conf_utils import Conf, SSPL_CONF, SSPL_LL_SETTING
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests


resource_id = "IEMSensor"
resource_type = "node:sw:cortx_sw_services:sspl"
test_iem_file = Conf.get(SSPL_CONF, f"{resource_id.upper()}>log_file_path")


def init(args):
    pass


def get_maximum_recovery_time(module_name):
    """
    Read sspl config for corresponding module recovery configs.

    Common sensor recovery config will be override by individual
    module recovery config.
    """
    recovery_count = Conf.get(
        SSPL_CONF, f"{SSPL_LL_SETTING}>sensor_recovery_count", 0)
    recovery_interval = Conf.get(
        SSPL_CONF, f"{SSPL_LL_SETTING}>sensor_recovery_interval", 0)
    # Override common recovery config if individual module has it
    recovery_count = Conf.get(
        SSPL_CONF,
        f"{module_name.upper()}>sensor_recovery_count", recovery_count)
    recovery_interval = Conf.get(
        SSPL_CONF,
        f"{module_name.upper()}>sensor_recovery_interval", recovery_interval)
    return recovery_count * recovery_interval


def send_thread_controller_actuator_request(module_name, state):
    request = {
        "username":"sspl-ll",
        "expires":3600,
        "description":"Seagate Storage Platform Library - Actuator Request",
        "title":"SSPL-LL Actuator Request",
        "signature":"None",
        "time":"2021-08-20 12:23.10.071170",
        "message":{
            "sspl_ll_msg_header":{
                "msg_version":"1.0.0",
                "uuid": str(uuid.uuid4()),
                "schema_version":"1.0.0",
                "sspl_version":"1.0.0"
            },
            "sspl_ll_debug":{
                "debug_component":"sensor",
                "debug_enabled": True
            },
            "response_dest": {},
            "target_node_id": get_current_node_id(),
            "actuator_request_type": {
                "thread_controller": {
                    "module_name": module_name,
                    "thread_request": state
                }
            }
        }
    }
    world.sspl_modules[EgressProcessorTests.name()]._write_internal_msgQ(
        EgressProcessorTests.name(), request)


def execute_module_thread_operation(action, thread_response, wait_time=None, resp_timeout=60):
    """
    Restart sensor module via thread controller and wait till
    'Restart Successful' message in response.
    """
    if wait_time:
        # Send thread controller request after the wait time
        time.sleep(wait_time)
    send_thread_controller_actuator_request(resource_id, action)
    thread_controller_resp = None
    start_time = time.time()

    while not thread_controller_resp:
        if not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
            ingressMsg = world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()
            try:
                # Make sure we get back the message type that matches the request
                msg_type = ingressMsg.get("actuator_response_type")
                if msg_type["thread_controller"]["module_name"] == resource_id:
                    print(f"Received: {ingressMsg}")
                    thread_controller_resp = msg_type
            except Exception as exception:
                print(exception)
        if (time.time()-start_time) > resp_timeout:
            break
        time.sleep(0.5)

    tc = thread_controller_resp.get("thread_controller")
    assert tc
    assert tc.get("module_name") == resource_id
    assert tc.get("thread_response") == thread_response


def simulate_IEM_sensor_failure():
    """Remove IEM log message file for raising fault alert."""
    if os.path.exists(test_iem_file):
        os.remove(test_iem_file)


def simulate_IEM_sensor_recovery():
    """Create IEM log message file for raising fault_resolved alert."""
    if not os.path.exists(test_iem_file):
        with open(test_iem_file, "w") as f:
            f.write("")


def test_sensor_unrecoverable_failure_alert(args):
    """Check for fault alert on unrecoverable sensor module failure."""
    check_sspl_ll_is_running()
    simulate_IEM_sensor_failure()
    # Wait until know its unrecoverable error
    ingressMsg = get_fru_response(resource_type, resource_id,
                                  ingress_msg_type="sensor_response_type",
                                  timeout=get_maximum_recovery_time(resource_id),
                                  alert_type="fault")
    sensor_msg = ingressMsg.get("sensor_response_type")
    assert sensor_msg
    assert sensor_msg.get("alert_type") == "fault"
    assert sensor_msg.get("severity") == "critical"
    assert sensor_msg.get("host_id")
    assert sensor_msg.get("info")
    info = sensor_msg.get("info")
    assert info
    assert info.get("site_id")
    assert info.get("node_id")
    assert info.get("rack_id")
    assert info.get("event_time")
    assert info.get("impact") is not None
    assert info.get("recommendation") == "Restart SSPL service"
    assert info.get("description") is not None
    assert info.get("resource_type") == resource_type
    assert info.get("resource_id") == resource_id


def test_sensor_unrecoverable_failure_no_repeat_alert(args):
    """
    Ensure the persistent cache check works on current and previous
    state of the module and doesn't repeat alert if already raised.
    """
    simulate_IEM_sensor_failure()
    execute_module_thread_operation(action="restart",
                                    thread_response="Restart Successful")
    try:
        ingressMsg = get_fru_response(resource_type, resource_id,
                                      ingress_msg_type="sensor_response_type",
                                      timeout=get_maximum_recovery_time(resource_id),
                                      alert_type="fault")
    except Exception as err:
        assert "Failed to get expected response message" in str(err)
    else:
        raise Exception(f"Response received unexpectedly: {ingressMsg}")


def test_sensor_recovery_success(args):
    """
    Check for fault resolved type alert on successful recovery
    of sensor module.
    """
    simulate_IEM_sensor_recovery()
    execute_module_thread_operation(action="restart",
                                    thread_response="Restart Successful")
    execute_module_thread_operation(action="status",
                                    thread_response="Status: Running",
                                    wait_time=get_maximum_recovery_time(resource_id))


test_list = [
    test_sensor_unrecoverable_failure_alert,
    test_sensor_unrecoverable_failure_no_repeat_alert,
    test_sensor_recovery_success
    ]
