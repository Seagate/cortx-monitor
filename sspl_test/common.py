#!/usr/bin/python3.6

"""
 ****************************************************************************
 Filename:          common.py
 Description:       Common utility functions of test infrastructure

 Creation Date:     22/05/2018
 Author:            Malhar Vora
                    Ujjwal Lanjewar

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import inspect
import traceback
import json
import time
import sys
import os
import psutil
from threading import Thread
from sspl_test.default import *

from sspl_test.framework.utils.config_reader import ConfigReader
from sspl_test.framework.utils.service_logging import init_logging
from sspl_test.framework.utils.service_logging import logger

# Adding sspl and sspl_test path
test_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.sys.path.append(os.path.join(test_path))
os.sys.path.append(os.path.join(test_path + "/../"))

from sspl_test.rabbitmq.rabbitmq_ingress_processor_tests import RabbitMQingressProcessorTests
from sspl_test.rabbitmq.rabbitmq_egress_processor import RabbitMQegressProcessor

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    import queue as queue
else:
    import Queue as queue

# Section and key in config file for bootstrap
SSPL_SETTING    = 'SSPL-TESTS_SETTING'
MODULES         = 'modules'
SYS_INFORMATION = 'SYSTEM_INFORMATION'
PRODUCT_NAME    = 'product'

class TestFailed(Exception):
    def __init__(self, desc):
        desc = '[%s] %s' %(inspect.stack()[1][3], desc)
        super(TestFailed, self).__init__(desc)

def init_rabbitMQ_msg_processors():
    """The main bootstrap for sspl automated tests"""

    # Retrieve configuration file for sspl-ll service
    path_to_conf_file = "/opt/seagate/eos/sspl/sspl_test/conf/sspl_tests.conf"
    if os.path.exists(path_to_conf_file):
        print("Using conf file : {}".format(path_to_conf_file))
    else:
        conf_directory = os.path.dirname(os.path.abspath(__file__))
        path_to_conf_file = os.path.join(conf_directory, "sspl_tests.conf")
        print("Using conf file : {}".format(path_to_conf_file))

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
    logger.info("sspl-ll Bootstrap: product name supported: %s" % product)

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
            logger.info("SSPL-Tests Starting %s" % curr_module.name())
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

# Common method used by test to check sspl service state
def check_sspl_ll_is_running():
    # Check that the state for sspl service is active
    found = False

    # Support for python-psutil < 2.1.3
    for proc in psutil.process_iter():
        if proc.name == "sspl_ll_d" and \
           proc.status in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
               found = True

    # Support for python-psutil 2.1.3+
    if found == False:
        for proc in psutil.process_iter():
            pinfo = proc.as_dict(attrs=['cmdline', 'status'])
            if "sspl_ll_d" in str(pinfo['cmdline']) and \
                pinfo['status'] in (psutil.STATUS_RUNNING, psutil.STATUS_SLEEPING):
                    found = True

    assert found == True

    # Clear the message queue buffer out
    while not world.sspl_modules[RabbitMQingressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[RabbitMQingressProcessorTests.name()]._read_my_msgQ()

def stop_rabbitMQ_msg_processors():
    """Shuts down rabbitmq threads and terminates tests"""
    time.sleep(5)
    print("SSPL Automated Test Process ended successfully")
    for name, module in list(world.sspl_modules.items()):
        module.shutdown()
    os._exit(0)
