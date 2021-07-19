import unittest
import socket
from unittest.mock import patch, Mock
from solution.lr2.server.manifest import ServerManifest


class TestServerManifest(unittest.TestCase):
    _server_manifest = None

    @classmethod
    @patch(
        "framework.platforms.server.platform.Platform."
        "validate_server_type_support", new=Mock(return_value=True)
    )
    def create_server_manifest_obj(cls):
        if cls._server_manifest is None:
            cls._server_manifest = ServerManifest()
        return cls._server_manifest

    def test_get_server_manifest_info(self):
        server_map = self.create_server_manifest_obj()
        resp = server_map.get_data('node>compute[0]')
        sys_resp = resp[0]["hw"]["systems"][0]
        assert sys_resp["uid"] == socket.gethostname()
        assert sys_resp["type"] == "system"

if __name__ == "__main__":
    unittest.main()
