"""
 ****************************************************************************
 Filename:          egress_accumulated_msgs_processor.py
 Description:       This processor handles acuumalted messages in consul
                    This keeps on running periodicaly and check if there is
                    any message to be sent to messaging bus system.
                    If message broker connection is availble message will 
                    be sent, else in next iteration it will be retried.
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

from framework.messaging.utils import get_messaging_config
from framework.base.sspl_constants import ServiceTypes, COMMON_CONFIGS
from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger
from framework.utils.store_queue import store_queue
from framework.utils.messaging_factory import messaging_factory

class EgressAccumulatedMsgsProcessor(ScheduledModuleThread, InternalMsgQ):
    """Send any unsent message to messaging"""

    MODULE_NAME = "EgressAccumulatedMsgsProcessor"
    PRIORITY    = 1

    MESSAGINGPROCESSOR           = 'EGRESSPROCESSOR'
    MESSAGINGPROCESSOR           = MODULE_NAME.upper()
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

        # Get common messaging config
        messaging_config = get_messaging_config(section=self.MESSAGINGPROCESSOR, 
                    keys=[(self.VIRT_HOST, "SSPL"), (self.EXCHANGE_NAME, "sspl-out"), 
                    (self.QUEUE_NAME, "sensor-queue"), (self.ROUTING_KEY, "sensor-key")])
        self._comm = messaging_factory.get_messaging_producer(**messaging_config)
        
        # No of message processed
        self._message_count = 0

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""
        logger.debug(f"{self.MODULE_NAME} Consul accumulated messages processing started")
        processed_message_count = 0
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
                    processed_message_count += 1
                self._comm.stop()
        except AmqpConnectionError as e:
            logger.error(f"{self.MODULE_NAME} {e}")
        except Exception as e:
            logger.error(f"{self.MODULE_NAME} {e}")
        finally:
            logger.debug(f"{self.MODULE_NAME} {processed_message_count} message processed")
            logger.debug(f"{self.MODULE_NAME} Consul accumulated processing ended")
            self._scheduler.enter(30, self._priority, self.run, ())

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(EgressAccumulatedMsgsProcessor, self).shutdown()
        self._comm.stop()
