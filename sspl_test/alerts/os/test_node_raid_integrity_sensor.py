import json
import os
from time import sleep
import sys

from sspl_test.default import *
from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor
from sspl_test.common import check_sspl_ll_is_running, check_os_platform


def init(args):
    pass

def test_raid_integrity_sensor(args):
    platform = check_os_platform()
    if platform == "vm":
        return
    check_sspl_ll_is_running()
    node_data_sensor_message_request("node:os:raid_integrity")
    raid_data_msg = None
    sleep(10)
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        ingressMsg = world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()
        sleep(0.1)
        print("Received for raid_integrity_data: {0}".format(ingressMsg))
        try:
            # Make sure we get back the message type that matches the request
            msg_type = ingressMsg.get("sensor_response_type")
            if msg_type.get("info").get("resource_type") == "node:os:raid_integrity":
                raid_data_msg = msg_type
                break
        except Exception as exception:
            sleep(0.1)
            print(exception)

    assert(raid_data_msg is not None)
    assert(raid_data_msg.get("alert_type") is not None)
    assert(raid_data_msg.get("alert_id") is not None)
    assert(raid_data_msg.get("severity") is not None)
    assert(raid_data_msg.get("host_id") is not None)
    assert(raid_data_msg.get("info") is not None)
    assert(raid_data_msg.get("specific_info") is not None)

    info = raid_data_msg.get("info")
    assert(info.get("site_id") is not None)
    assert(info.get("node_id") is not None)
    assert(info.get("cluster_id") is not None)
    assert(info.get("rack_id") is not None)
    assert(info.get("resource_type") is not None)
    assert(info.get("event_time") is not None)
    assert(info.get("resource_id") is not None)

    specific_info = raid_data_msg.get("specific_info")
    assert(specific_info.get("error") is None)


def node_data_sensor_message_request(sensor_type):
    egressMsg = {
        "title": "SSPL Actuator Request",
        "description": "Seagate Storage Platform Library - Actuator Request",

        "username" : "JohnDoe",
        "signature" : "None",
        "time" : "2015-05-29 14:28:30.974749",
        "expires" : 500,

        "message" : {
            "sspl_ll_msg_header": {
                "schema_version": "1.0.0",
                "sspl_version": "1.0.0",
                "msg_version": "1.0.0"
            },
             "sspl_ll_debug": {
                "debug_component" : "sensor",
                "debug_enabled" : True
            },
            "sensor_request_type": {
                "node_data": {
                    "sensor_type": sensor_type
                }
            }
        }
    }

    world.sspl_modules[RabbitMQegressProcessor.name()]._write_internal_msgQ(RabbitMQegressProcessor.name(), egressMsg)

test_list = [test_raid_integrity_sensor]
