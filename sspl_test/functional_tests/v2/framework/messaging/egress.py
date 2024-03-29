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

import json

from cortx.utils.message_bus import MessageProducer

from framework.utils.service_logging import logger
from framework.utils.conf_utils import Conf, SSPL_TEST_CONF


class TestEgressProcessor:
    """Handles outgoing messages via messaging over localhost."""

    MODULE_NAME = "EgressProcessorTests"
    PRIORITY = 1

    # Section and keys in configuration file
    SYSTEM_INFORMATION = "SYSTEM_INFORMATION"
    RACK_ID = "rack_id"
    NODE_ID = "node_id"
    CLUSTER_ID = "cluster_id"
    SITE_ID = "site_id"

    PROCESSOR = MODULE_NAME.upper()
    SIGNATURE_USERNAME = "message_signature_username"
    SIGNATURE_TOKEN = "message_signature_token"
    SIGNATURE_EXPIRES = "message_signature_expires"
    IEM_ROUTE_ADDR = "iem_route_addr"
    PRODUCER_ID = "producer_id"
    MESSAGE_TYPE = "message_type"
    METHOD = "method"

    def __init__(self):
        self._request_shutdown = False
        self._msg_sent_succesfull = True
        # Configure messaging Exchange to transmit messages
        self._connection = None
        self._read_config()
        self._producer = MessageProducer(
            producer_id=self._producer_id,
            message_type=self._message_type,
            method=self._method,
        )

    def _read_config(self):
        """Configure the messaging exchange with defaults available."""
        try:
            self._signature_user = Conf.get(
                SSPL_TEST_CONF, f"{self.PROCESSOR}>{self.SIGNATURE_USERNAME}", "sspl-ll"
            )
            self._signature_token = Conf.get(
                SSPL_TEST_CONF,
                f"{self.PROCESSOR}>{self.SIGNATURE_TOKEN}",
                "FAKETOKEN1234",
            )
            self._signature_expires = Conf.get(
                SSPL_TEST_CONF, f"{self.PROCESSOR}>{self.SIGNATURE_EXPIRES}", "3600"
            )
            self._producer_id = Conf.get(
                SSPL_TEST_CONF, f"{self.PROCESSOR}>{self.PRODUCER_ID}", "sspl-sensor"
            )
            self._message_type = Conf.get(
                SSPL_TEST_CONF, f"{self.PROCESSOR}>{self.MESSAGE_TYPE}", "Alerts"
            )
            self._method = Conf.get(
                SSPL_TEST_CONF, f"{self.PROCESSOR}>{self.METHOD}", "Sync"
            )

        except Exception as ex:
            logger.error("EgressProcessorTests, _read_config: %r" % ex)

    def publish(self, msg):
        """Transmit json message onto messaging exchange."""
        msg = json.dumps(msg)
        self._producer.send([msg])
