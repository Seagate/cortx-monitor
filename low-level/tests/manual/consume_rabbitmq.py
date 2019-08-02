#!/usr/bin/python3.6
from .manual_test import ManualTest

manTest = ManualTest("RABBITMQEGRESSPROCESSOR", start_threads=False)
manTest.basicConsume()
