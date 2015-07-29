"""
 ****************************************************************************
 Filename:          debug.py
 Description:       Flags and methods for handling debug mode
 Creation Date:     02/09/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import json
from framework.utils.service_logging import logger
from systemd import journal

class Debug(object):
    """"Flags and methods for handling debug mode"""

    def __init__(self):
        super(Debug, self).__init__()
        self._debug = False
        self._debug_persist = False

    def _log_debug(self, message):
        """Logging messages"""
        if self._debug:
            log_msg = self.name() + ", " + message
            journal.send(log_msg, PRIORITY=7, SYSLOG_IDENTIFIER="sspl-ll")

    def _set_debug(self, debug):
        """Sets debug flag"""
        if self._debug_persist == False:
            self._debug = debug

    def _get_debug(self):
        """Returns the debug flag"""
        return self._debug

    def _set_debug_persist(self, debug_persist):
        """Sets debug persist flag"""
        self._debug_persist = debug_persist

    def _get_debug_persist(self):
        """Returns debug persist flag"""
        return self._debug_persist

    def _disable_debug_if_persist_false(self):
        """Turn debug mode off if persistence is False"""
        if self._debug_persist == False:
            self._debug = False

    def _check_debug(self, jsonMsgRaw):
        """Examines the optional debug section in json msg and turns on/off debug mode

        Returns True if the only line in the sspl_ll_debug section is 
        "debug_enabled" : false signifying that all threads should turn
        debug mode persistence off and reset to default startup"""

        # Handle raw strings
        if isinstance(jsonMsgRaw, dict) == False:
            jsonMsg = json.loads(jsonMsgRaw)
        else:
            jsonMsg = jsonMsgRaw

        # Handle case for optional debug_enabled for keeping debug persistent
        # TODO: Break this apart into small methods to make it easier to understand
        if jsonMsg.get("sspl_ll_debug") is not None and \
            jsonMsg.get("sspl_ll_debug").get("debug_enabled") is not None:
                #logger.info("%s, _check_debug, debug_enabled: %s" % (self.name(), jsonMsgRaw))

                if jsonMsg.get("sspl_ll_debug").get("debug_enabled") == False:
                    #logger.info("%s, _check_debug, debug_enabled is False" % self.name())
                    self._set_debug_persist(False)

                    #logger.info("_check_debug, debug_component: %s" % \
                    #            jsonMsg.get("sspl_ll_debug").get("debug_component"))

                    # If no debug_component line then flag to turn debug off globally
                    if jsonMsg.get("sspl_ll_debug").get("debug_component") is None:
                        #logger.info("%s, _check_debug, Turn debug off globally" % self.name())
                        return (True, None)

                    # Internal msg sent to turn debug mode off on all modules
                    elif jsonMsg.get("sspl_ll_debug").get("debug_component") == "all":
                        #logger.info("%s, _check_debug, debug_component is all" % self.name())
                        return (False, None)

                    # If it's an valid msg being processed then it will have a sspl_ll_msg_header section
                    elif jsonMsg.get("sspl_ll_msg_header") is not None:
                        return (False, jsonMsg)

                elif jsonMsg.get("sspl_ll_debug").get("debug_enabled") == True:
                    self._set_debug(True)
                    self._set_debug_persist(True)

                    # TODO: See if there is no debug_component and set all modules to debug mode
                    #return (True, jsonMsg)
        else:
             # Handle case for having an optional debug_component; we want granularity in modules      
             if jsonMsg.get("sspl_ll_debug") is not None and \
                jsonMsg.get("sspl_ll_debug").get("debug_component") is not None:
                    #logger.info("%s, _check_debug, debug_enabled: %s" % (self.name(), jsonMsgRaw))                    
                    self._set_debug(True)
             # Check to see if persistent debug is set, if not then turn debug mode off
             elif self._get_debug_persist() == False:
                 self._set_debug(False)

        return (False, jsonMsg)
