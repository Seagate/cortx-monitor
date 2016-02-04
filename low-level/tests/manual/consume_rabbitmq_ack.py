#!/usr/bin/env python
from manual_test import ManualTest

manTest = ManualTest("RABBITMQINGRESSPROCESSOR", start_threads=False)
manTest.basicConsumeAck()
