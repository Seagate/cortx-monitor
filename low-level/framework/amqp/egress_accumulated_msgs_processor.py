"""
 ****************************************************************************
 Filename:          egress_accumulated_msgs_processor.py
 Description:       This processor handles acuumalted messages in consul
                    This keeps on running periodicaly and check if there is
                    any message to be sent to rabbtmq. If rabbitmq connection
                    is availble message will be sent, else in next iteration
                    it will be retried.
 Creation Date:     03/19/2020
 Author:            Sandeep Anjara

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by
 Seagate Technology, LLC.
 ****************************************************************************
"""
import sys

import pika
import json
import time

from eos.utils.amqp import AmqpConnectionError

from framework.amqp.utils import get_amqp_common_config
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.utils.store_queue import store_queue
from framework.utils.amqp_factory import amqp_factory

class EgressAccumulatedMsgsProcessor(ScheduledModuleThread, InternalMsgQ):
    """Send any unsent message to amqp"""

    MODULE_NAME = "EgressAccumulatedMsgsProcessor"
    PRIORITY    = 1

    AMQPPROCESSOR           = 'EGRESSPROCESSOR'
    AMQPPROCESSOR           = MODULE_NAME.upper()
    VIRT_HOST               = 'virtual_host'

    EXCHANGE_NAME           = 'exchange_name'
    QUEUE_NAME              = 'queue_name'
    ROUTING_KEY             = 'routing_key'


    # 300 seconds for 5 mins
    MSG_TIMEOUT = 300

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return EgressAccumulatedMsgsProcessor.MODULE_NAME


    def __init__(self):
        super(EgressAccumulatedMsgsProcessor, self).__init__(
            self.MODULE_NAME, self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread
        super(EgressAccumulatedMsgsProcessor, self).initialize(conf_reader)

        super(EgressAccumulatedMsgsProcessor, self).initialize_msgQ(msgQlist)

        # Get common amqp config
        amqp_config = self._get_amqp_config()
        self._comm = amqp_factory.get_amqp_producer(**amqp_config)


    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""
        logger.debug(f"{self.MODULE_NAME} Consul accumulated messages processing started")
        try:
            if not store_queue.is_empty():
                logger.debug(f"{self.MODULE_NAME} Found accumulated messages, trying to send again")
                self._comm.init()
                while not store_queue.is_empty():
                    message = store_queue.get()
                    dict_msg = json.loads(message)
                    if "actuator_response_type" in dict_msg["message"]:
                        event_time = dict_msg["message"]["actuator_response_type"]["info"]["event_time"]
                        time_diff = int(time.time()) - int(event_time)
                        if time_diff > self.MSG_TIMEOUT:
                            continue
                    self._comm.send(dict_msg)
                self._comm.stop()
        except AmqpConnectionError as e:
            logger.error(f"{self.MODULE_NAME} {e}")
        except Exception as e:
            logger.error(f"{self.MODULE_NAME} {e}")
        finally:
            logger.debug(f"{self.MODULE_NAME} Consul accumulated processing ended")
            self._scheduler.enter(30, self._priority, self.run, ())

    def _get_amqp_config(self):
        module_specific_config = {
            "virtual_host": self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                            self.VIRT_HOST, 'SSPL'),
            "exchange": self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                            self.EXCHANGE_NAME, 'sspl-out'),
            "exchange_queue": self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                            self.QUEUE_NAME, 'sensor-queue'),
            "exchange_type": "topic",
            "routing_key": self._conf_reader._get_value_with_default(self.AMQPPROCESSOR,
                                                            self.ROUTING_KEY, 'sensor-key'),
            "durable": True,
            "exclusive": False,
            "retry_count": 1,
        }
        amqp_common_config = get_amqp_common_config()
        return { **module_specific_config, **amqp_common_config }

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(EgressAccumulatedMsgsProcessor, self).shutdown()
        self._comm.stop()
