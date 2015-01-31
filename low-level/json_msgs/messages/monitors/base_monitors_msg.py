"""
 ****************************************************************************
 Filename:          base_monitor_msg.py
 Description:       All monitor JSON messages extend this base class
                    containing global constants used throughout  
 Creation Date:     01/31/2015
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

import os
import abc
from jsonschema import Draft4Validator
from json_msgs.messages.base_msg import BaseMsg
from json_msgs.schemas import monitors 

class BaseMonitorMsg(BaseMsg):
    '''
    The base class for all JSON monitor messages transmitted by SSPL-LL
    '''

    TITLE               = "SSPL-LL Monitor Response"
    DESCRIPTION         = "Seagate Storage Platform Library - Low Level - Monitor Response"
    JSON_MONITOR_SCHEMA = "SSPL-LL_Monitor_Response"


    def __init__(self):
        super(BaseMonitorMsg, self).__init__()
          
        # Read in the monitor schema for validating messages
        fileName = os.path.join(monitors.__path__[0],
                                self.JSON_MONITOR_SCHEMA)        
        with open(fileName, 'r') as f:
            self._schema = f.read()
            
          
    @abc.abstractmethod        
    def getJson(self):
        """Force all sub-classes to implement"""
        pass
    
    
    def validateMsg(self):                
        #TODO: Get validation working against json messages
        #Draft4Validator.check_schema(self._schema)
        pass
        