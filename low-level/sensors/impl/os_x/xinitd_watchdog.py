"""
 ****************************************************************************
 Filename:          xinitd_watchdog.py
 Description:       Monitors Mac OS xinitd for service events and notifies
                    the ServiceMsgHandler
 Creation Date:     04/27/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""
import os
import json
import shutil
import Queue
import pyinotify

from framework.base.module_thread import ScheduledModuleThread
from framework.base.internal_msgQ import InternalMsgQ
from framework.utils.service_logging import logger

# Modules that receive messages from this module
from message_handlers.service_msg_handler import ServiceMsgHandler

from zope.interface import implements
from sensors.IService_watchdog import IServiceWatchdog

import dbus
from dbus import SystemBus, Interface
import gobject
from dbus.mainloop.glib import DBusGMainLoop
from systemd import journal


class XinitdWatchdog(ScheduledModuleThread, InternalMsgQ):

    implements(IServiceWatchdog)

    MODULE_NAME       = "XinitdWatchdog"
    PRIORITY          = 2

    # Section and keys in configuration file
    XINITDWATCHDOG = MODULE_NAME.upper()
    MONITORED_SERVICES = 'monitored_services'


    @staticmethod
    def name():
        """@return: name of the module."""
        return XinitdWatchdog.MODULE_NAME

    def __init__(self):
        super(XinitdWatchdog, self).__init__(self.MODULE_NAME,
                                                  self.PRIORITY)
        # Mapping of services and their status'
        self._service_status = {}

    def initialize(self, conf_reader, msgQlist):
        """initialize configuration reader and internal msg queues"""

        # Initialize ScheduledMonitorThread and InternalMsgQ
        super(XinitdWatchdog, self).initialize(conf_reader)

        # Initialize internal message queues for this module
        super(XinitdWatchdog, self).initialize_msgQ(msgQlist)

    def read_data(self):
        """Return the dict of service status'"""
        return self._service_status

    def run(self):
        """Run the monitoring periodically on its own thread."""
        # Check for debug mode being activated
        self._read_my_msgQ_noWait()

        self._set_debug(True)
        self._set_debug_persist(True)

        self._log_debug("Start accepting requests")

        try:            
            # TODO: loop here forever monitoring for service changes
            self._log_debug("XinitdWatchdog monitoring service events")

        except Exception as ae:
            # Check for debug mode being activated when it breaks out of blocking loop
            self._read_my_msgQ_noWait()
            if self.is_running() == True:
                self._log_debug("XinitdWatchdog ungracefully breaking " \
                                "out of dbus Loop, restarting: %r" % ae)
                self._scheduler.enter(1, self._priority, self.run, ())

        # Reset debug mode if persistence is not enabled
        self._disable_debug_if_persist_false()

        self._log_debug("Finished processing successfully")

    
    def shutdown(self):
        """Clean up scheduler queue and gracefully shutdown thread"""
        super(XinitdWatchdog, self).shutdown()
        try:
            self._log_debug("XinitdWatchdog, shutdown")

            # Break out of dbus loop
            self._running = False

        except Exception:
            logger.info("XinitdWatchdog, shutting down.")