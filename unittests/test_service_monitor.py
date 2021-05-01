


import os
import sys
from threading import Thread
import time
import unittest
from unittest.mock import Mock, MagicMock, patch


from cortx.utils.kv_store.kv_payload import KvPayload
from cortx.utils.service import DbusServiceHandler

PROJECT_ROOT = "/".join(os.path.abspath(__file__).split("/")
                        [:-2]) + "/low-level"
sys.path.append(PROJECT_ROOT)

from sensors.impl.centos_7.service_monitor_im import ServiceMonitor, Conf, Interface, Service

class TestServiceMonitor(unittest.TestCase):

    def setUp(self):
        self.mocked_conf_values = {
            "SERVICEMONITOR>monitored_services": ["dummy_service.service"],
            "SERVICEMONITOR>thread_sleep": "1",
            "SERVICEMONITOR>polling_frequency": "5",
            "SERVICEMONITOR>threshold_inactive_time": "3",
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
        # thread = Thread(target=self.service_monitor.run)
        # thread.start()

    def mocked_conf(self, *args, **kwargs):
        key = args[1]
        return self.mocked_conf_values[key]

    def test_state_transition_alert(self):
        states = (("reloading", "active", 2),
                  ("reloading", "failed", 0),
                  ("active", "failed", 0),
                  ("deactivating", "failed", 0),
                  ("deactivating", "active", 2),
                  ("inactive", "failed", 0),
                  ("inactive", "active", 2),
                  ("failed", "active", 2),
                  ("activating", "inactive", 0),
                  ("activating", "deactivating", 0),
                  ("activating", "active", 2),
                  ("activating", "failed", 0),
                  )
        
        for state in states:
            service = MagicMock()
            service.state = state[0]
            service.properties_iface.Get.return_value = state[1]

            self.service_monitor.update_properties("","","", service)
            service.get_alert.assert_called_with(state[2])
    def test_obj(self):
        # Interface.return_value =
        Interface.Get = Mock()
        s = Service("dummy_servsice.service")


    def tearDown(self):
        self.service_monitor.is_running = Mock(return_value=False)


t = TestServiceMonitor()
t.setUp()

if __name__ == "__main__":
    unittest.main()