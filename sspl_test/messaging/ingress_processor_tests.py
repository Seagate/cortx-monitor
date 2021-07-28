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
import os
import time
import socket
import traceback

from jsonschema import Draft3Validator
from jsonschema import validate

from cortx.utils.message_bus import MessageConsumer

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.base.sspl_constants import RESOURCE_PATH

from framework.utils.conf_utils import Conf, SSPL_TEST_CONF, NODE_ID_KEY

import ctypes
from . import producer_initialized

SSPL_SEC = ctypes.cdll.LoadLibrary('libsspl_sec.so.0')


class IngressProcessorTests():
    """Handles incoming messages via messaging for automated tests."""

    MODULE_NAME = "IngressProcessorTests"
    PRIORITY = 1

    # Section and keys in configuration file
    PROCESSOR = MODULE_NAME.upper()
    CONSUMER_ID = "consumer_id"
    CONSUMER_GROUP = "consumer_group"
    MESSAGE_TYPE = "message_type"
    OFFSET = "offset"
    SYSTEM_INFORMATION_KEY = 'SYSTEM_INFORMATION'

    JSON_ACTUATOR_SCHEMA = "SSPL-LL_Actuator_Response.json"
    JSON_SENSOR_SCHEMA = "SSPL-LL_Sensor_Response.json"

    def __init__(self):
        self._read_config()
        self._consumer = MessageConsumer(consumer_id=self._consumer_id,
                                         consumer_group=self._consumer_group,
                                         message_types=[self._message_type],
                                         auto_ack=True, offset=self._offset)

    def message_reader(self):
        logger.info("Started reading messages")
        try:
            while True:
                message = self._consumer.receive()
                if message:
                    logger.info(f"IngressProcessorTests, Message Received: {message}")
                    self._consumer.ack()
                    yield json.loads(message)['message']
                else:
                    time.sleep(.2)
        except Exception as e:
            logger.error("IngressProcessorTests, Exception: %s" % str(e))
            logger.error(traceback.format_exc())

    def _read_config(self): 
        """Configure the messaging exchange with defaults available."""
        # Make methods locally available
        self._node_id = Conf.get(SSPL_TEST_CONF, NODE_ID_KEY, 'SN01')
        self._consumer_id = Conf.get(SSPL_TEST_CONF,
                                     f"{self.PROCESSOR}>{self.CONSUMER_ID}",
                                     'sspl_actuator')
        self._consumer_group = Conf.get(SSPL_TEST_CONF,
                                        f"{self.PROCESSOR}>{self.CONSUMER_GROUP}",
                                        'cortx_monitor')
        self._message_type = Conf.get(SSPL_TEST_CONF,
                                      f"{self.PROCESSOR}>{self.MESSAGE_TYPE}",
                                      'Requests')
        self._offset = Conf.get(SSPL_TEST_CONF,
                                f"{self.PROCESSOR}>{self.OFFSET}",
                                'earliest')

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(IngressProcessorTests, self).shutdown()
