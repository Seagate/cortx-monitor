#!/usr/bin/env python

from manual_test import ManualTest

manTest = ManualTest("RABBITMQINGRESSPROCESSOR")
manTest.basicPublish(jsonfile = "tests/manual/actuator_msgs/real_stor_actuator.json",
        response_wait_time=240)
