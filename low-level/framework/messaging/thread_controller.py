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

"""
 ****************************************************************************
  Description:       Provides the ability to manipulate running threads
                    within the framework.
 ****************************************************************************
"""

import json
import os
import time
import traceback
from socket import gethostname
from threading import Thread

from framework.base.internal_msgQ import InternalMsgQ
from framework.base.module_thread import (ScheduledModuleThread, SensorThread,
    SensorThreadState)
from framework.base.sspl_constants import (OperatingSystem, cs_legacy_products,
    cs_products, enabled_products, DATA_PATH)
# Import modules to control
from framework.messaging.egress_processor import \
    EgressProcessor
from framework.messaging.ingress_processor import \
    IngressProcessor
from framework.utils.conf_utils import (
    GLOBAL_CONF, SSPL_CONF, Conf, SSPL_LL_SETTING, NODE_ID_KEY)
from framework.utils.service_logging import logger
from json_msgs.messages.actuators.thread_controller import ThreadControllerMsg
from json_msgs.messages.sensors.thread_monitor_msg import ThreadMonitorMsg
from message_handlers.disk_msg_handler import DiskMsgHandler
# Note that all threaded message handlers must have an import here to be controlled
from message_handlers.node_controller_msg_handler import \
    NodeControllerMsgHandler
from message_handlers.node_data_msg_handler import NodeDataMsgHandler
from message_handlers.real_stor_actuator_msg_handler import \
    RealStorActuatorMsgHandler
from message_handlers.real_stor_encl_msg_handler import RealStorEnclMsgHandler
from message_handlers.service_msg_handler import ServiceMsgHandler
from framework.utils.store_factory import store

module_persistent_data = {}
module_cache_dir = os.path.join(DATA_PATH, "modules")
node_id = Conf.get(GLOBAL_CONF, NODE_ID_KEY, "SN01")


def _get_recovery_config(module_name):
    """
    Read sspl config for corresponding module recovery configs.

    Common sensor recovery config will be overriden by individual
    module recovery config.
    """
    recovery_count = Conf.get(
        SSPL_CONF, f"{SSPL_LL_SETTING}>sensor_recovery_count", 0)
    recovery_interval = Conf.get(
        SSPL_CONF, f"{SSPL_LL_SETTING}>sensor_recovery_interval", 0)
    # Override common recovery config if individual module has it
    recovery_count = Conf.get(
        SSPL_CONF,
        f"{module_name.upper()}>sensor_recovery_count", recovery_count)
    recovery_interval = Conf.get(
        SSPL_CONF,
        f"{module_name.upper()}>sensor_recovery_interval", recovery_interval)
    return recovery_count, recovery_interval


# Global method used by Thread to capture and log errors.  This must be global.
def execute_thread(module, msgQlist, conf_reader, product, resume=True):
    """
    Run module as a thread. Recover the module if any error during
    initialization and run time of the module.

    If recovery count>0,
        module will be recovered from failure until the maximum recovery
        attempt. If not recoverable, corresponding module will be shutdown
        and failure alert will be raised due to its impact.
    If recovery count=0,
        no recovery attempt will be made.
    """
    module_name = module.name()
    # Suspend module threads
    if resume == False:
        module.suspend()

    # Initialize persistent cache for sensor status
    per_data_path = os.path.join(
        module_cache_dir, f"{module_name.upper()}_{node_id}")
    if not os.path.isfile(per_data_path):
        module_persistent_data[module_name] = {}
        store.put(module_persistent_data[module_name], per_data_path)

    is_sensor_thread = False
    recovery_count = recovery_interval = 0
    if isinstance(module, SensorThread):
        recovery_count, recovery_interval = _get_recovery_config(module_name)
        is_sensor_thread = True

    attempt = 0

    while attempt <= recovery_count:
        attempt += 1
        try:
            # Each module is passed a reference list to message queues so it
            # can transmit internal messages to other modules as desired
            module.start_thread(conf_reader, msgQlist, product)
        except Exception as err:
            curr_state = "fault"
            err_msg = f"{module_name}, {err}"
            logger.error(err_msg)
            if attempt > recovery_count:
                logger.debug(traceback.format_exc())
                description = f"{module_name} is stopped and unrecoverable. {err_msg}"
                impact = module.impact()
                recommendation = "Restart SSPL service"
                logger.critical(
                    f"{description}. Impact: {impact} Recommendation: {recommendation}")
                # Check previous state of the module and send fault alert
                if os.path.isfile(per_data_path):
                    module_persistent_data[module_name] = store.get(per_data_path)
                prev_state = module_persistent_data[module_name].get('prev_state')
                if is_sensor_thread and curr_state != prev_state:
                    module_persistent_data[module_name] = {"prev_state": curr_state}
                    store.put(module_persistent_data[module_name], per_data_path)
                    specific_info = Conf.get(SSPL_CONF, f"{module_name.upper()}")
                    info = {
                        "module_name": module_name,
                        "alert_type": curr_state,
                        "description": description,
                        "impact": impact,
                        "recommendation": recommendation,
                        "severity": "critical",
                        "specific_info": specific_info
                    }
                    jsonMsg = ThreadMonitorMsg(info).getJson()
                    module._write_internal_msgQ(EgressProcessor.name(), jsonMsg)
            else:
                logger.debug(f"Recovering {module_name} from failure, "
                             f"attempt: {attempt}")
                time.sleep(recovery_interval)

            # Shutdown if no recovery attempt
            logger.info(f"Terminating monitoring thread {module_name}")
            module.shutdown()
            retry = 5
            while module.is_running():
                module.shutdown()
                retry -= 1
                if not retry:
                    break
                time.sleep(2)


def _check_module_recovered(module):
    """
    Once SSPL is restarted, check current status of the module after
    certain recovery cycle time. If module is running and its previous
    state is fault, raise fault_resolved alert and update cache.
    """
    module_name = module.name()
    # Wait till sensor module completes few run cycle. Then
    # raise module recovery fault_resolved alert.
    polling_cycle_time = Conf.get(
        SSPL_CONF, f"{SSPL_LL_SETTING}>sensor_polling_cycle_time", 60)
    time.sleep(polling_cycle_time)
    if not module.is_running():
        return

    curr_state = "fault_resolved"
    per_data_path = os.path.join(
        module_cache_dir, f'{module_name.upper()}_{node_id}')
    if not os.path.isfile(per_data_path):
        module_persistent_data[module_name] = {}
        store.put(module_persistent_data[module_name], per_data_path)
    # Check previous state before sending fault resolved alert
    module_persistent_data[module_name] = store.get(per_data_path)
    prev_state = module_persistent_data[module_name].get('prev_state')
    if prev_state and curr_state != prev_state:
        module_persistent_data[module_name] = {"prev_state": curr_state}
        store.put(module_persistent_data[module_name], per_data_path)
        specific_info = Conf.get(SSPL_CONF, f"{module_name.upper()}")
        info = {
            "module_name": module_name,
            "alert_type": curr_state,
            "description": f"{module_name} is recovered",
            "impact": "",
            "recommendation": "",
            "severity": "info",
            "specific_info": specific_info
        }
        jsonMsg = ThreadMonitorMsg(info).getJson()
        module._write_internal_msgQ(EgressProcessor.name(), jsonMsg)


class ThreadController(ScheduledModuleThread, InternalMsgQ):

    MODULE_NAME = "ThreadController"
    PRIORITY = 1

    # Section and keys in configuration file
    THREADCONTROLLER = MODULE_NAME.upper()
    ALWAYS_ACTIVE_MODULES = [
        "EgressProcessor", "IngressProcessor",
        "ThreadController"
    ]

    # Constats for keys to read from conf file
    SSPL_SETTING = 'SSPL_LL_SETTING'
    DEGRADED_STATE_MODULES = 'degraded_state_modules'

    @staticmethod
    def name():
        """ @return: name of the monitoring module."""
        return ThreadController.MODULE_NAME

    def __init__(self):
        super(ThreadController, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        self._threads_initialized = False
        self._thread_response = "N/A"
        self.debug_section = None

        # Location of hpi data directory populated by dcs-collector
        self._hpi_base_dir = "/tmp/dcs/hpi"
        self._start_delay = 10
        self._systemd_support = True
        self._hostname = gethostname()
        self._modules_to_resume = []

    def get_sspl_module(self, module):
        try:
            return self._sspl_modules[module]
        except KeyError:
            return None

    def initialize(self, conf_reader, msgQlist, product):
        """initialize configuration reader and internal msg queues"""
        # Initialize ScheduledMonitorThread
        super(ThreadController, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(ThreadController, self).initialize_msgQ(msgQlist)
        self._modules_to_resume = self._get_degraded_state_modules_list()

    def initialize_thread_list(self, sspl_modules, operating_system, product,
                               systemd_support):
        """initialize list of references to all modules"""
        self._sspl_modules = sspl_modules
        self._product = product
        self._operating_system = operating_system
        self._systemd_support = systemd_support

        if operating_system == OperatingSystem.CENTOS7.value or operating_system == OperatingSystem.RHEL7.value or \
            operating_system.lower() in OperatingSystem.CENTOS7.value.lower() or operating_system.lower() in OperatingSystem.RHEL7.value.lower():
            # Note that all threaded sensors and actuators must have an
            # import here to be controlled
            from sensors.impl.centos_7.disk_monitor import DiskMonitor
            from sensors.impl.centos_7.service_monitor import ServiceMonitor
            from sensors.impl.centos_7.drive_manager import DriveManager
            from sensors.impl.centos_7.hpi_monitor import HPIMonitor

        # Handle configurations for specific products
        if product.lower() == "cs-a":
            from sensors.impl.generic.SMR_drive_data import SMRdriveData
        if product.lower() in [x.lower() for x in enabled_products]:
            from sensors.impl.platforms.realstor.realstor_disk_sensor \
                import RealStorDiskSensor
            from sensors.impl.platforms.realstor.realstor_psu_sensor \
                import RealStorPSUSensor
            from sensors.impl.platforms.realstor.realstor_fan_sensor \
                import RealStorFanSensor
            from sensors.impl.platforms.realstor.realstor_controller_sensor \
                import RealStorControllerSensor
            from sensors.impl.platforms.realstor.realstor_sideplane_expander_sensor \
                import RealStorSideplaneExpanderSensor
            from sensors.impl.platforms.realstor.realstor_dg_volume_sensor \
                import RealStorLogicalVolumeSensor
            from sensors.impl.platforms.realstor.realstor_enclosure_sensor \
                import RealStorEnclosureSensor
            from sensors.impl.generic.raid import RAIDsensor
            from sensors.impl.generic.raid_integrity_data import RAIDIntegritySensor

    def run(self):
        """Run the module periodically on its own thread."""
        if (self._product.lower() in [x.lower() for x in enabled_products]) and \
           not self._threads_initialized:
            if self._product.lower() in [x.lower() for x in cs_products]:
                # Wait for the dcs-collector to populate the /tmp/dcs/hpi directory
                while not os.path.isdir(self._hpi_base_dir):
                    logger.info(
                        "ThreadController, dir not found: %s " % self._hpi_base_dir)
                    logger.info(
                        "ThreadController, rechecking in %s secs" % self._start_delay)
                    time.sleep(int(self._start_delay))

            logger.debug("ThreadController._sspl_modules is {}".format(
                self._sspl_modules))
            # Allow other threads to initialize
            continue_waiting = False
            for (n,m) in self._sspl_modules.items():
                if not isinstance(m, SensorThread):
                    continue
                thread_init_status = m.get_thread_init_status()
                logger.debug("Thread status for {} is {}".format(
                    m.__class__, thread_init_status))
                if thread_init_status == SensorThreadState.WAITING:
                    continue_waiting = True

            if continue_waiting:
                logger.debug("ThreadController, waiting for all modules to initialize")
                self._scheduler.enter(10, self._priority, self.run, ())
                return

            # Notify external applications that've started up successfully
            startup_msg = "SSPL service has started successfully"
            json_msg = ThreadControllerMsg(ThreadController.name(), startup_msg).getJson()
            self._write_internal_msgQ(EgressProcessor.name(), json_msg)
            self._threads_initialized = True

            # Check sensor module is recovered from previous failure
            for module in self._sspl_modules.values():
                if not isinstance(module, SensorThread):
                    continue
                module_checker = Thread(target=_check_module_recovered,
                                        args=(module,))
                module_checker.start()

            #self._set_debug(True)
            #self._set_debug_persist(True)
            self._log_debug("Start accepting requests")
        try:
            # Block on message queue until it contains an entry
            jsonMsg, _ = self._read_my_msgQ()
            if jsonMsg is not None:
                self._process_msg(jsonMsg)

            # Keep processing until the message queue is empty
            while not self._is_my_msgQ_empty():
                jsonMsg, _ = self._read_my_msgQ()
                if jsonMsg is not None:
                    self._process_msg(jsonMsg)
        except Exception as ex:
            # Log it and restart the whole process when a failure occurs
            logger.exception("ThreadController restarting: %r" % ex)

        self._scheduler.enter(1, self._priority, self.run, ())
        self._log_debug("Finished processing successfully")

    def _process_msg(self, jsonMsg):
        """Parses the incoming message and calls the appropriate method"""
        self._log_debug("_process_msg, jsonMsg: %s" % jsonMsg)

        # Check to see if debug mode is being globally turned off on all modules
        if self._check_reset_all_modules(jsonMsg) is True:
            return

        # Parse out the module name and request
        module_name    = jsonMsg.get("actuator_request_type").get("thread_controller").get("module_name")
        thread_request = jsonMsg.get("actuator_request_type").get("thread_controller").get("thread_request")

        # Parse out the uuid so that it can be sent back in Ack message
        uuid = None
        if jsonMsg.get("sspl_ll_msg_header") is not None and \
           jsonMsg.get("sspl_ll_msg_header").get("uuid") is not None:
            uuid = jsonMsg.get("sspl_ll_msg_header").get("uuid")
            self._log_debug("_processMsg, uuid: %s" % uuid)

        # Pass along the debug section to the module
        if jsonMsg.get("sspl_ll_debug") is not None:
            self.debug_section = { "sspl_ll_debug": {}}
            self.debug_section["sspl_ll_debug"] = jsonMsg.get("sspl_ll_debug")
        else:
            self.debug_section = None

        self._log_debug("_process_msg, self.debug_section: %s" % self.debug_section)

        # Parse out thread request and call the appropriate method
        if thread_request == "restart":
            self._restart_module(module_name)
        elif thread_request == "start":
            self._start_module(module_name)
        elif thread_request == "stop":
            # Don't let the outside world stop us or shut down this thread
            if module_name == "EgressProcessor" or \
                module_name == "IngressProcessor" or \
                module_name == "ThreadController":
                    logger.warn("Attempt to stop message processors or ThreadController Processors, \
                                    ignoring. Please try 'restart' instead.")
                    return
            self._stop_module(module_name)
        elif thread_request == "status":
            self._status_module(module_name)
        elif thread_request == "degrade":
            if module_name.lower() != "all":
                logger.warn(
                    "Invalid module_name {0}. Need 'all' in module_name"
                    .format(module_name))
                return
            self._switch_to_degraded_state(self._sspl_modules)
        elif thread_request == "active":
            if module_name.lower() != "all":
                logger.warn(
                    "Invalid module_name {0}. Need 'all' in module_name"
                    .format(module_name))
                return
            self._switch_to_active_state(self._sspl_modules)
        else:
            self._thread_response = "Error, unrecognized thread request"

        node_id = []
        if jsonMsg.get("actuator_request_type").get("thread_controller").get("parameters") is not None and \
           jsonMsg.get("actuator_request_type").get("thread_controller").get("parameters").get("node_id"):
            node_id = jsonMsg.get("actuator_request_type").get("thread_controller").get("parameters").get("node_id")

        ack_type = {}
        ack_type["hostname"] = self._hostname
        ack_type["node_id"] = node_id

        # Populate an actuator response message and transmit
        threadControllerMsg = ThreadControllerMsg(module_name, self._thread_response, \
                                                  json.dumps(ack_type))

        if uuid is not None:
            threadControllerMsg.set_uuid(uuid)
        msgString = threadControllerMsg.getJson()
        logger.info("ThreadController, response: %s" % str(msgString))
        if self._product.lower() in [x.lower() for x in enabled_products]:
            self._write_internal_msgQ(EgressProcessor.name(), msgString)
        elif self._product.lower() in [x.lower() for x in cs_legacy_products]:
            self._write_internal_msgQ(EgressProcessor.name(), msgString)

    def _restart_module(self, module_name):
        """Restart a module"""
        self._log_debug("_restart_module, module_name: %s" % module_name)

        try:
            # Stop the module if it's running and let existing thread die gracefully
            if self._status_module(module_name) is True:
                self._stop_module(module_name)

            # Allow module a few seconds to shut down gracefully
            max_wait  = 10
            curr_wait = 1
            while self._status_module(module_name) is True:
                time.sleep(3)
                logger.info("Retrying: %s" % str(curr_wait))
                self._stop_module(module_name)
                curr_wait += 1
                if curr_wait > max_wait:
                    break

            # Start the module
            self._start_module(module_name)
        except Exception as ae:
            logger.warn("Restart thread failed: %s" % str(ae))
            self._thread_response = "Restart Failed"
        else:
            self._thread_response = "Restart Successful"

    def _switch_to_degraded_state(self, modules):
        """Shifts SSPL to degraded state. Essentially it calls a suspend of
           every module every running in an independent thread
        """
        self._log_debug("_switch_to_degraded_state, modules: %s" % modules)
        if not modules:
            raise TypeError("module parameter can't be None")
        try:
            for name, module_instance in modules.items():
                if not name in self._modules_to_resume:
                    module_instance.suspend()
            self._thread_response = "Degrade Successful"
        except Exception as e:
            logger.warn("Degrade operation failed: {0}".format(e))
            self._thread_response = "Degrade failed"

    def _switch_to_active_state(self, modules):
        """Shifts SSPL to active state. Essentially it calls a resume of
           every module every running in an independent thread
        """
        self._log_debug("_switch_to_active_state, modules: %s" % modules)
        if not modules:
            raise TypeError("module parameter can't be None")
        try:
            for name, module_instance in modules.items():
                module_instance.resume()
            self._thread_response = "Active Successful"
        except Exception as e:
            logger.error("Active operation failed: {0}".format(e))
            self._thread_response = "Active failed"

    def _stop_module(self, module_name):
        """Stop a module"""
        self._log_debug("_stop_module, module_name: %s" % module_name)

        try:
            if self._status_module(module_name) is False:
                self._log_debug("_stop_module, status: False")
                return

            self._thread_response = "Stop Successful"

            # Put a debug message on the module's queue before shutting it down
            if self.debug_section is not None:
                self._write_internal_msgQ(module_name, self.debug_section)

            # Call the module's shutdown method for a graceful halt
            self._sspl_modules[module_name].shutdown()
        except Exception as ae:
            logger.warn("Stop thread failed: %s" % str(ae))
            self._thread_response = "Stop Failed"

    def _start_module(self, module_name):
        """Start a module"""
        self._log_debug("_start_module, module_name: %s" % module_name)

        try:
            if self._status_module(module_name) is True:
                self._log_debug("_start_module, status: True")
                return

            self._thread_response = "Start Successful"

            # NOTE: This is internal code that is currently unused.
            # If this is brought into use again its interaction
            # with the init dependency code will need to be considered
            module_thread = Thread(target=execute_thread,
                                   args=(self._sspl_modules[module_name],
                                         self._msgQlist, self._conf_reader,
                                         self._product))

            # Put a configure debug message on the module's queue before starting it up
            if self.debug_section is not None:
                self._write_internal_msgQ(module_name, self.debug_section)

            module_thread.start()
        except Exception as ae:
            logger.warn("Start thread failed: %s" % str(ae))
            self._thread_response = "Start Failed"

    def _status_module(self, module_name):
        """Returns if the module is running or not"""
        if self._sspl_modules[module_name].is_running() is True:
            self._thread_response = "Status: Running"
        else:
            self._thread_response = "Status: Halted"

        self._log_debug("_status_module, module_name: %s, _thread_response: %s" %
                        (module_name, self._thread_response))
        return self._sspl_modules[module_name].is_running()

    def _check_reset_all_modules(self, jsonMsg):
        """Restarts all modules with debug mode off. Activated by internal_msgQ"""
        if jsonMsg.get("sspl_ll_debug") is not None and \
            jsonMsg.get("sspl_ll_debug").get("debug_component") is not None and \
            jsonMsg.get("sspl_ll_debug").get("debug_component") == "all":
                for module in self._sspl_modules:
                    self._log_debug("_check_reset_all_modules, module: %s" % module)
                    # Don't restart this thread or it won't complete the loop
                    if module != self.name():
                        self._restart_module(module)

                # Populate an actuator response message and transmit
                msgString = ThreadControllerMsg("All Modules", "Restarted with debug mode off").getJson()
                self._write_internal_msgQ(EgressProcessor.name(), msgString)
                return True

        return False

    def shutdown_all_modules(self):
        """Calls shutdown for all modules"""
        logger.info("Shutting down all modules")
        for name, other_module in list(self._sspl_modules.items()):
            other_module.shutdown()

    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(ThreadController, self).shutdown()

    def check_EgressProcessor_is_running(self):
        """Used by the shutdown_handler to allow queued egress msgs to complete"""
        if self._product.lower() in [x.lower() for x in enabled_products]:
            return self._sspl_modules[EgressProcessor.name()].is_running()
        elif self._product.lower() in [x.lower() for x in cs_legacy_products]:
            return self._sspl_modules[EgressProcessor.name()].is_running()

    def _get_degraded_state_modules_list(self):
        """Reads list of modules to run in degraded state and returns a list
           of those modules.
        """
        # List of modules to run in degraded mode
        modules_to_resume = []
        try:
            # Read list of modules from conf file to load in degraded mode
            modules_to_resume = Conf.get(SSPL_CONF,
                f"{self.SSPL_SETTING}>{self.DEGRADED_STATE_MODULES}", [])
        except Exception as e:
            logger.warn("ThreadController: Configuration not found,"
                "degraded_state_modules")
        return modules_to_resume
