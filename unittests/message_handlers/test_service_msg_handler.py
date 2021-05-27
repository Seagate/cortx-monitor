import unittest

from message_handlers.service_msg_handler import ServiceMsgHandler


class TestServiceMsgHandler(unittest.TestCase):
    service_info = {
            'service_name': 'kafka',
            'status': 'failed'
        }

    def setUp(self) -> None:
        self.service_msg_handler = ServiceMsgHandler()
        self.service_msg_handler.cluster_id = 1
        self.service_msg_handler.site_id = 1
        self.service_msg_handler.rack_id = 1
        self.service_msg_handler.node_id = 1
        self.service_msg_handler.storage_set_id = 1
        self.service_msg_handler.host_id = 1

    def test_create_actuator_response(self):
        resp_msg = self.service_msg_handler._create_actuator_response(self.service_info)
        assert resp_msg['host_id'] == 1
        assert resp_msg['instance_id'] == 'kafka'
        assert resp_msg['specific_info'][0]['service_name'] == 'kafka'
        assert resp_msg['specific_info'][0]['status'] == 'failed'
        assert resp_msg['alert_type'] == 'UPDATE'
        assert resp_msg['info']['resource_type'] == 'node:sw:os:service'
