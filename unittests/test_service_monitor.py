import os
import sys
import unittest
from threading import Thread
from unittest.mock import Mock

PROJECT_ROOT = "/".join(os.path.abspath(__file__).split("/")
                        [:-2]) + "/low-level"
sys.path.append(PROJECT_ROOT)

from sensors.impl.centos_7.service_monitor import (ServiceMonitor, Conf)


class TestServiceMonitor(unittest.TestCase):

    def setUp(self):
        self.mocked_conf_values = {
            "SERVICEMONITOR>monitored_services": ["dummy_service.service"],
            "SERVICEMONITOR>thread_sleep": "1",
            "SERVICEMONITOR>polling_frequency": "5",
            "SERVICEMONITOR>threshold_inactive_time": "10",
            "cluster>srvnode-1>site_id": "DC01",
            "cluster>srvnode-1>rack_id": "RC01",
            "cluster>srvnode-1>node_id": "SN01",
            "cluster>cluster_id": "CC01"
        }
        Conf.get = Mock(side_effect=self.mocked_conf)
        self.service_monitor = ServiceMonitor()
        self.service_monitor.initialize(Mock(), Mock(), Mock())
        self.service_monitor.is_running = Mock(return_value=True)
        self.service_monitor._write_internal_msgQ = Mock()
        thread = Thread(target=self.service_monitor.run)
        thread.start()

    def mocked_conf(self, *args, **kwargs):
        key = args[1]
        return self.mocked_conf_values[key]

    def tearDown(self):
        self.service_monitor.is_running = Mock(return_value=False)


if __name__ == "__main__":
    unittest.main()
