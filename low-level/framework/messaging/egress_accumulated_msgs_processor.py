"""
 ****************************************************************************
 Filename:          egress_accumulated_msgs_processor.py
 Description:       This processor handles acuumalted messages in consul
                    This keeps on running periodicaly and check if there is
                    any message to be sent to rabbtmq. If message bus connection
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
import json
import time

from cortx.utils.message_bus import MessageProducer
from cortx.utils.message_bus.error import MessageBusError

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import ScheduledModuleThread
from framework.utils.conf_utils import SSPL_CONF, Conf
from framework.utils.service_logging import logger
from framework.utils.store_queue import StoreQueue
from . import producer_initialized


class EgressAccumulatedMsgsProcessor(ScheduledModuleThread, InternalMsgQ):
    """Send any unsent message to message bus."""

    SENSOR_NAME = "EgressAccumulatedMsgsProcessor"
    PRIORITY    = 1

    # TODO: read egress config from common place
    # Section and keys in configuration file
    # Section and keys in configuration file
    PROCESSOR = 'EgressProcessor'
    SIGNATURE_USERNAME = 'message_signature_username'
    SIGNATURE_TOKEN = 'message_signature_token'
    SIGNATURE_EXPIRES = 'message_signature_expires'
    IEM_ROUTE_ADDR = 'iem_route_addr'
    PRODUCER_ID = 'producer_id'
    MESSAGE_TYPE = 'message_type'
    METHOD = 'method'
    # 300 seconds for 5 mins
    MSG_TIMEOUT = 300

    @staticmethod
    def name():
        """@return: name of the monitoring module."""
        return EgressAccumulatedMsgsProcessor.SENSOR_NAME

    def __init__(self):
        super(EgressAccumulatedMsgsProcessor, self).__init__(
            self.SENSOR_NAME, self.PRIORITY)

    def initialize(self, conf_reader, msgQlist, products):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread
        super(EgressAccumulatedMsgsProcessor, self).initialize(
            conf_reader)

        super(EgressAccumulatedMsgsProcessor, self).initialize_msgQ(
            msgQlist)

        self.store_queue = StoreQueue()
        self._read_config()
        producer_initialized.wait()
        self._producer = MessageProducer(producer_id="acuumulated processor",
                                         message_type=self._message_type,
                                         method=self._method)

    def read_data(self):
        """This method is part of interface. Currently it is not
        in use.
        """
        return {}

    def run(self):
        """Run the sensor on its own thread"""
        logger.debug("Consul accumulated messages processing started")
        if not self._is_my_msgQ_empty():
            # Check for shut down message from sspl_ll_d and set a flag to shutdown
            #  once our message queue is empty
            self._jsonMsg, _ = self._read_my_msgQ()
            if self._jsonMsg.get("message").get(
                    "actuator_response_type") is not None and \
                    self._jsonMsg.get("message").get(
                        "actuator_response_type").get(
                        "thread_controller") is not None and \
                    self._jsonMsg.get("message").get(
                        "actuator_response_type").get("thread_controller").get(
                        "thread_response") == \
                    "SSPL-LL is shutting down":
                logger.info(
                    "EgressAccumulatedMsgsProcessor, run, received"
                    "global shutdown message from sspl_ll_d")
                self.shutdown()
        try:
            # TODO : Fix accumulated message processor when message bus changes are available to
            # error out in case of failure (EOS-17626)
            if not self.store_queue.is_empty():
                logger.debug("Found accumulated messages, trying to send again")
                while not self.store_queue.is_empty():
                    message = self.store_queue.get()
                    dict_msg = json.loads(message)
                    if "actuator_response_type" in dict_msg["message"]:
                        event_time = dict_msg["message"] \
                            ["actuator_response_type"]["info"]["event_time"]
                        time_diff = int(time.time()) - int(event_time)
                        if time_diff > self.MSG_TIMEOUT:
                            continue
                    if "sensor_response_type" in dict_msg["message"]:
                        logger.info(f"Publishing Accumulated Alert: {message}")
                    self._producer.send([message])
        except MessageBusError as e:
            logger.error("EgressAccumulatedMsgsProcessor, run, %r" % e)
        except Exception as e:
            logger.error(e)
        finally:
            logger.debug("Consul accumulated processing ended")
            self._scheduler.enter(30, self._priority, self.run, ())

    def _read_config(self):
        """Read config for messaging bus."""
        try:
            self._signature_user = Conf.get(SSPL_CONF,
                                            f"{self.PROCESSOR}>{self.SIGNATURE_USERNAME}",
                                            'sspl-ll')
            self._signature_token = Conf.get(SSPL_CONF,
                                             f"{self.PROCESSOR}>{self.SIGNATURE_TOKEN}",
                                             'FAKETOKEN1234')
            self._signature_expires = Conf.get(SSPL_CONF,
                                               f"{self.PROCESSOR}>{self.SIGNATURE_EXPIRES}",
                                               "3600")
            self._producer_id = Conf.get(SSPL_CONF,
                                         f"{self.PROCESSOR}>{self.PRODUCER_ID}",
                                         "sspl-sensor")
            self._message_type = Conf.get(SSPL_CONF,
                                          f"{self.PROCESSOR}>{self.MESSAGE_TYPE}",
                                          "alerts")
            self._method = Conf.get(SSPL_CONF,
                                    f"{self.PROCESSOR}>{self.METHOD}",
                                    "sync")
        except Exception as ex:
            logger.error("EgressProcessor, _read_config: %r" % ex)

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(EgressAccumulatedMsgsProcessor, self).shutdown()
        self._connection.cleanup()
