"""
 ****************************************************************************
 Filename:          internal_msgQ.py
 Description:       Base class used for reading and writing to internal
                    message queues for modules to communication with one
                    another.
 Creation Date:     02/09/2015
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

from utils.service_logging import logger

class InternalMsgQ(object):
    """Base Class for internal message queue communications between modules"""

    def __init__(self):
        super(InternalMsgQ, self).__init__()
    
    def initializeMsgQ(self, msgQlist):
        """Initialize the map of internal message queues"""
        self._msgQlist = msgQlist
    
    def _isMyMsgQempty(self):
        """Returns True/False for this module's queue being empty"""        
        q = self._msgQlist[self.name()]
        return q.empty()
    
    def _readMyMsgQ(self):
        """Reads a json message from this module's queue placed by another thread"""        
        q = self._msgQlist[self.name()]
        jsonMsg = q.get()
        logger.info("_readMyMsgQ: %s, Msg:%s" % (self.name(), jsonMsg))
        return jsonMsg
    
    def _writeInternalMsgQ(self, toModule, jsonMsg):
        """writes a json message to an internal message queue"""
        try:
            logger.info("_writeInternalMsgQ: From %s, To %s, Msg:%s" % 
                        (self.name(), toModule, jsonMsg))
            q = self._msgQlist[toModule]
            q.put(jsonMsg)           
        
        except Exception as ex:
            logger.exception("_writeInternalMsgQ: %s" % ex)
    
        
        
        