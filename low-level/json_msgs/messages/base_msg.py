"""
 ****************************************************************************
 Filename:          base_msg.py
 Description:       All transmitted JSON messages extend this base class
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
"""

import abc

class BaseMsg(metaclass=abc.ABCMeta):
    '''
    The base class for all JSON messages transmitted by SSPL-LL
    '''


    SCHEMA_VERSION  = "1.0.0"
    SSPL_VERSION    = "1.0.0"


    def __init__(self):
        pass

    @abc.abstractmethod
    def getJson(self):
        raise NotImplementedError("Subclasses should implement this!")

    def normalize_kv(self, item):
        """Normalize all keys coming from firmware from - to _"""
        if isinstance(item, dict):
            return {key.replace("-", "_"): self.normalize_kv(value) for key, value in item.items()}
        elif isinstance(item, list):
            return [self.normalize_kv(_) for _ in item]
        elif item == "N/A":
            return "NA"
        else:
            return item
