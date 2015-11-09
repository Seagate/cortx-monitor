#!/usr/bin/env python

from manual_test import ManualTest

manTest = ManualTest("RABBITMQEGRESSPROCESSOR")
manTest.basicPublish(jsonfile = "actuator_msgs/node_cntrl_hdparm.json")
