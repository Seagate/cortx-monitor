from lettuce import *

import json
import time
import logging
import daemon
import signal
import queue
import sys
import os

from threading import Thread

# Add the top level directory to the sys.path to access classes
topdir = os.path.dirname(os.path.dirname(os.path.dirname \
            (os.path.dirname(os.path.abspath(__file__)))))
os.sys.path.insert(0, topdir)


from framework.utils.config_reader import ConfigReader
from framework.utils.service_logging import init_logging
from framework.utils.service_logging import logger

from test.automated.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from framework.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

# Section and key in config file for bootstrap
SSPL_SETTING    = 'SSPL-TESTS_SETTING'
MODULES         = 'modules'
SYS_INFORMATION = 'SYSTEM_INFORMATION'
PRODUCT_NAME    = 'product'

@before.all
def init_rabbitMQ_msg_processors():
    """The main bootstrap for sspl automated tests"""

    # Retrieve configuration file for sspl-ll service
    conf_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path_to_conf_file = os.path.join(conf_directory, "sspl_tests.conf")
    try:
        conf_reader = ConfigReader(path_to_conf_file)
    except (IOError, ConfigReader.Error) as err:
        # We don't have logger yet, need to find log_level from conf file first
        print("[ Error ] when validating the configuration file %s :" % \
            path_to_conf_file)
        print(err)
        print("Exiting ...")
        exit(os.EX_USAGE)

    # Initialize logging
    try:
        init_logging("SSPL-Tests", "DEBUG")

    except Exception as err:
        # We don't have logger since it threw an exception, use generic 'print'
        print("[ Error ] when initializing logging :")
        print(err)
        print("Exiting ...")
        exit(os.EX_USAGE)

    # Modules to be used for testing
    conf_modules = conf_reader._get_value_list(SSPL_SETTING,
                                                MODULES)

    # Create a map of references to all the module's message queues.  Each module
    #  is passed this mapping so that it can send messages to other modules.
    msgQlist = {}

    # Create a mapping of all the instantiated modules to their names
    world.sspl_modules = {}

    # Read in product value from configuration file
    product = conf_reader._get_value(SYS_INFORMATION, PRODUCT_NAME)
    logger.info("SSPL Bootstrap: product name supported: %s" % product)

    # Use reflection to instantiate the class based upon its class name in config file
    for conf_thread in conf_modules:
        klass = globals()[conf_thread]

        # Create mappings of modules and their message queues
        world.sspl_modules[klass.name()] = klass()
        msgQlist[klass.name()] = queue.Queue()

    # Convert to a dict
    # TODO: Check use of this
    world.diskmonitor_file = json.loads("{}")

    try:
        # Loop through the list of instanced modules and start them on threads
        threads=[]
        for name, curr_module in list(world.sspl_modules.items()):
            logger.info("SSPL Tests Starting %s" % curr_module.name())
            curr_module._set_debug(True)
            thread = Thread(target=_run_thread_capture_errors,
                            args=(curr_module, msgQlist, conf_reader, product))
            thread.start()
            threads.append(thread)

        # Allow threads to startup before running tests
        time.sleep(2)

        # Clear the message queue buffer out from msgs sent at startup
        while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
            world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

    except Exception as ex:
        logger.exception(ex)


# Global method used by Thread to capture and log errors.  This must be global.
def _run_thread_capture_errors(curr_module, msgQlist, conf_reader, product):
    """Run the given thread and log any errors that happen on it.
    Will stop all sspl_modules if one of them fails."""
    try:
        # Each module is passed a reference list to message queues so it can transmit
        #  internal messages to other modules as desired
        curr_module.initialize(conf_reader, msgQlist, product)
        curr_module.start()

    except BaseException as ex:
        logger.critical("SSPL-Tests encountered a fatal error, terminating service Error: %s" % ex)
        logger.exception(ex)

        # Populate an actuator response message and transmit back to HAlon
        error_msg = "SSPL-Tests encountered an error, terminating service Error: " + \
                    ", Exception: " + logger.exception(ex)
        jsonMsg   = ThreadControllerMsg(curr_module, error_msg).getJson()
        curr_module._write_internal_msgQ(RabbitMQegressProcessor.name(), jsonMsg)

        # Shut it down, error is non-recoverable
        for name, other_module in list(world.sspl_modules.items()):
            if other_module is not curr_module:
                other_module.shutdown()

@after.all
def stop_rabbitMQ_msg_processors(self):
    """Shuts down rabbitmq threads and terminates tests"""
    time.sleep(5)
    print("SSPL Automated Test Process ended successfully")
    for name, module in list(world.sspl_modules.items()):
        module.shutdown()
    os._exit(0)
