#!/usr/bin/env python
from manual_test import ManualTest

manTest = ManualTest("RABBITMQEGRESSPROCESSOR", start_threads=False)
manTest.basicConsume()
