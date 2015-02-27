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
from utils.service_logging import logger


class Debug(object):
    """"Flags and methods for handling debug mode"""

    def __init__(self):
        super(Debug, self).__init__()
        self._debug = False
        self._debug_persist = False

    def _log_debug(self, message):
        """Logging messages"""
        if self._debug:
            logger.info(self.name() + ", " + message)

    def _set_debug(self, debug):
        """Sets debug flag"""
        if self._debug_persist == False:
            self._debug = debug

    def _set_debug_persist(self, debug_persist):
        """Sets debug persist flag"""
        self._debug_persist = debug_persist

    def _get_debug_persist(self):
        """Returns debug persist flag"""
        return self._debug_persist

    def _check_debug(self, jsonMsgRaw):
        """Examines the optional debug section in json msg and turns on/off debug mode

        Returns True if the only line in the sspl_ll_debug section is 
        "debug_enabled" : false signifying that all threads should turn
        debug mode persistence off"""

        # Handle raw strings
        if type(jsonMsgRaw) != dict:
            jsonMsg = json.loads(jsonMsgRaw)
        else:
            jsonMsg = jsonMsgRaw

        # Handle case for optional debug_enabled for keeping debug persistent
        if jsonMsg.get("sspl_ll_debug") is not None and \
            jsonMsg.get("sspl_ll_debug").get("debug_enabled") is not None:
                if jsonMsg.get("sspl_ll_debug").get("debug_enabled") == False:
                    self._set_debug_persist(False)

                    # If no debug_component line then flag to turn debug off globally
                    if jsonMsg.get("sspl_ll_debug").get("debug_component") is None:
                        return True
                    
                elif jsonMsg.get("sspl_ll_debug").get("debug_enabled") == True:
                    self._set_debug(True)
                    self._set_debug_persist(True)
        else:
             # Handle case for having an optional debug_component; we want granularity        
             if jsonMsg.get("sspl_ll_debug") is not None and \
                jsonMsg.get("sspl_ll_debug").get("debug_component") is not None:
                    self._set_debug(True)
             # Check to see if persistent debug is set, if not then turn debug mode off
             elif self._get_debug_persist() == False:
                 self._set_debug(False)

        return False
