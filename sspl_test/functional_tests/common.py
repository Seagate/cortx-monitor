#!/usr/bin/python3.6

# Copyright (c) 2018-2020 Seagate Technology LLC and/or its Affiliates
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


"""
 ****************************************************************************
  Description:       Common utility functions of test infrastructure
 ****************************************************************************
"""

import inspect
import subprocess
from sspl_constants import DEFAULT_NODE_ID
from framework.utils.conf_utils import (
    Conf,
    GLOBAL_CONF,
    NODE_ID_KEY,
)

# Section and key in config file for bootstrap
SSPL_SETTING = "SSPL-TESTS_SETTING"
MODULES = "modules"
SYS_INFORMATION = "SYSTEM_INFORMATION"
PRODUCT_NAME = "product"
conf_reader = None


class TestFailed(Exception):
    def __init__(self, desc):
        desc = "[%s] %s" % (inspect.stack()[1][3], desc)
        super(TestFailed, self).__init__(desc)


def get_current_node_id():
    """Get current node id."""
    node_id = Conf.get(GLOBAL_CONF, NODE_ID_KEY, DEFAULT_NODE_ID)
    return node_id


def check_os_platform():
    """Returns the os platform on which test-case is running"""
    CHECK_PLATFORM = " hostnamectl status | grep Chassis"
    process = subprocess.Popen(
        CHECK_PLATFORM, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    response, error = process.communicate()
    if response:
        output = response.decode().rstrip("\n")
        platform = output.split(":")[1].lstrip()
        return platform
    if error:
        print(
            "Failed to get the os platform: error:{}".format(
                error.decode().rstrip("\n")
            )
        )


def actuator_response_filter(msg, resource_type, resource_id=None):
    # import pdb; pdb.set_trace()
    msg_type = msg.get("actuator_response_type", None)
    try:
        if msg_type and msg_type["info"]["resource_type"] == resource_type:
            return True
        if resource_id:
            if (
                msg_type
                and msg_type["info"]["resource_type"] == resource_type
                and msg_type["info"]["resource_id"] == resource_id
            ):
                return True
    except KeyError:
        return False


def sensor_response_filter(msg, resource_type):
    # import pdb; pdb.set_trace()
    msg_type = msg.get("sensor_response_type", None)
    try:
        if msg_type and msg_type["info"]["resource_type"] == resource_type:
            return True
    except KeyError:
        return False


def get_node_controller_message_request(uuid, resource_type, instance_id="*"):
    """
    This method creates actuator request using resource_type and instance_id.

    The request will be written in EgressProcesser message Queue.
    param:
        uuid: Unique ID for the request
        resource_type: Type of resource
        instance_id: Numeric or "*"
    """
    return {
        "username": "sspl-ll",
        "expires": 3600,
        "description": "Seagate Storage Platform Library - Actuator Request",
        "title": "SSPL-LL Actuator Request",
        "signature": "None",
        "time": "2018-07-31 04:08:04.071170",
        "message": {
            "sspl_ll_msg_header": {
                "msg_version": "1.0.0",
                "uuid": uuid,
                "schema_version": "1.0.0",
                "sspl_version": "1.0.0",
            },
            "sspl_ll_debug": {"debug_component": "sensor", "debug_enabled": True},
            "response_dest": {},
            "target_node_id": get_current_node_id(),
            "actuator_request_type": {
                "node_controller": {
                    "node_request": resource_type,
                    "resource": instance_id,
                }
            },
        },
    }


def get_enclosure_request(resource_type, resource_id):
    return {
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
                "msg_version": "1.0.0",
            },
            "sspl_ll_debug": {"debug_component": "sensor", "debug_enabled": True},
            "request_path": {
                "site_id": "1",
                "rack_id": "1",
                "cluster_id": "1",
                "node_id": "1",
            },
            "response_dest": {},
            "target_node_id": get_current_node_id(),
            "actuator_request_type": {
                "storage_enclosure": {
                    "enclosure_request": resource_type,
                    "resource": resource_id,
                }
            },
        },
    }
