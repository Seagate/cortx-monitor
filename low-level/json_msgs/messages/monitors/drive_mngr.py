"""
 ****************************************************************************
 Filename:          drive_mngr.py
 Description:       Defines the JSON message transmitted by the
                    DriveManagerMonitor. There may be a time when we need to
                    maintain state as far as messages being transmitted.  This
                    may involve aggregation of multiple messages before
                    transmissions or simply deferring an acknowledgment to
                    a later point in time.  For this reason, the JSON messages
                    are stored as objects which can be queued up, etc.
 Creation Date:     01/30/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.

 ****************************************************************************
 All relevant license information (GPL, FreeBSD, etc)
 ****************************************************************************
"""

import json
from json_msgs.messages.monitors.base_monitors_msg import BaseMonitorMsg

class DriveMngrMsg(BaseMonitorMsg):
    '''
    The JSON message transmitted by the DriveManagerMonitor
    '''

    MONITOR_MSG_TYPE = "disk_status_drivemanager"

    def __init__(self, _enclosure,
                       _drive_num,
                       _status):
        super(DriveMngrMsg, self).__init__()         
        
        self._enclosure = _enclosure
        self._drive_num = _drive_num
        self._status    = _status        
        
        self._json = {"title" : self.TITLE,
                      "description" : self.DESCRIPTION,
                      "sspl_ll_host": {                        
                            "schema_version" : self.SCHEMA_VERSION,
                            "sspl_version" : self.SSPL_VERSION
                            },
                      "monitor_msg_type": {
                            self.MONITOR_MSG_TYPE: {
                                "enclosureSN" : self._enclosure,
                                "diskNum" : int(self._drive_num),                                            
                                "diskStatus": self._status                                
                                }
                            }                      
                      }
        
    def getJson(self):
        """Return a validated JSON object"""    
        # Validate the current message    
        self.validateMsg(self._json)       
        return json.dumps(self._json)
                 
    def getEnclosure(self):
        return self._enclosure
        
    def getDriveNum(self):
        return self._drive_num
        
    def getStatus(self):
        return self._status
    
    def setStatus(self, _status):
        self._status = _status
        