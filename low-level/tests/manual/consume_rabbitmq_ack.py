#!/usr/bin/env python
from manual_test import ManualTest

manTest = ManualTest("RABBITMQINGRESSPROCESSOR")
manTest.basicConsumeAck()
