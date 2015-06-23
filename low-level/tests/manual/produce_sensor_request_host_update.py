#!/usr/bin/env python

from manual_test import ManualTest

manTest = ManualTest("RABBITMQEGRESSPROCESSOR")
manTest.basicPublish(jsonfile = "actuator_msgs/sensor_request_host_update.json")
