import unittest
import socket
from unittest.mock import patch

from files.opt.seagate.sspl.setup.resource_map.lr2.server_manifest import ServerManifest


class TestServerManifest(unittest.TestCase):
    _server_manifest = None

    @classmethod
    def create_server_manifest_obj(cls):
        if cls._server_manifest is None:
            cls._server_manifest = ServerManifest()
        return cls._server_manifest

    def test_get_server_manifest_info(self):
        server_map = self.create_server_manifest_obj()
        resp = server_map.get_server_manifest_info()
        sys_resp = resp[0]["hw"]["systems"][0]
        assert sys_resp["uid"] == socket.gethostname()
        assert sys_resp["type"] == "system"

if __name__ == "__main__":
    unittest.main()
