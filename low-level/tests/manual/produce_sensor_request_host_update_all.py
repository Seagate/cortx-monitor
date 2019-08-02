#!/usr/bin/python3.6

from .manual_test import ManualTest

manTest = ManualTest("RABBITMQEGRESSPROCESSOR")
manTest.basicPublish(jsonfile = "actuator_msgs/sensor_request_host_update_all.json")
