#!/usr/bin/python3.6

# Copyright (c) 2018-2020 Seagate Technology LLC and/or its Affiliates
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


"""
 ****************************************************************************
  Description:       Common utility functions of test infrastructure
 ****************************************************************************
"""

import inspect
import traceback
import json
import time
import sys
import os
import psutil
import subprocess
from threading import Thread
from default import world
from framework.utils.service_logging import init_logging
from framework.utils.service_logging import logger
from messaging.ingress_processor_tests import IngressProcessorTests
from messaging.egress_processor_tests import EgressProcessorTests
from framework.utils.conf_utils import Conf, SSPL_TEST_CONF, GLOBAL_CONF, PRODUCT_KEY


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
conf_reader = None
class TestFailed(Exception):
    def __init__(self, desc):
        desc = '[%s] %s' %(inspect.stack()[1][3], desc)
        super(TestFailed, self).__init__(desc)

def init_messaging_msg_processors():
    """The main bootstrap for sspl automated tests"""

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
    conf_modules = Conf.get(SSPL_TEST_CONF, f"{SSPL_SETTING}>{MODULES}")

    # Create a map of references to all the module's message queues.  Each module
    #  is passed this mapping so that it can send messages to other modules.
    msgQlist = {}

    # Create a mapping of all the instantiated modules to their names
    world.sspl_modules = {}

    # Read in product value from configuration file
    product = Conf.get(GLOBAL_CONF, PRODUCT_KEY)
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
        while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
            world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()

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
        curr_module._write_internal_msgQ(EgressProcessorTests.name(), jsonMsg)

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
    while not world.sspl_modules[IngressProcessorTests.name()]._is_my_msgQ_empty():
        world.sspl_modules[IngressProcessorTests.name()]._read_my_msgQ()

def stop_messaging_msg_processors():
    """Shuts down messaging threads and terminates tests"""
    time.sleep(5)
    print("SSPL Automated Test Process ended successfully")
    for name, module in list(world.sspl_modules.items()):
        module.shutdown()
    os._exit(0)


def check_os_platform():
    """ Returns the os platform on which test-case is running"""
    CHECK_PLATFORM = " hostnamectl status | grep Chassis"
    process = subprocess.Popen(CHECK_PLATFORM, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    response, error = process.communicate()
    if response:
        output = response.decode().rstrip('\n')
        platform = output.split(":")[1].lstrip()
        return platform
    if error:
        print("Failed to get the os platform: error:{}".format(error.decode().rstrip('\n')))
