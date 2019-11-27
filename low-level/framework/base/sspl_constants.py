#!/usr/bin/env python
from enum import Enum

enabled_products = ["EES", "CS-A"]
cs_products = ["CS-A"]
cs_legacy_products = ["CS-L", "CS-G"]


class AlertTypes(Enum):
    GET = "get"


class SensorTypes(Enum):
    TEMPERATURE = "temperature"
    CURRENT = "current"
    VOLTAGE = "voltage"


class SeverityTypes(Enum):
    INFORMATIONAL = "informational"


class ResourceTypes(Enum):
    SENSOR = "sensor"
    INTERFACE = "interface"


class EnclInterface(Enum):
    SAS = "SAS"

if __name__ == "__main__":
    print(' '.join(enabled_products))
