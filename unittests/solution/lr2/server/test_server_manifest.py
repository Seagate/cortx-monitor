# Copyright (c) 2001-2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

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
        sys_resp = resp[0]["hw"]["system"][0]
        assert sys_resp["uid"] == socket.gethostname()
        assert sys_resp["type"] == "system"

if __name__ == "__main__":
    unittest.main()
