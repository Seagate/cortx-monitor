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

    def normalize_kv(self, jsonMsg):
        """Normalize all keys coming from firmware from - to _"""
        new_dic = {}
        for k, v in jsonMsg.items():
            if isinstance(v, dict):
                v = self.normalize_kv(v)
            elif isinstance(v, list):
                new_lst = []
                for d in v:
                    d = self.normalize_kv(d)
                    new_lst.append(d)
                v = new_lst
            new_dic[k.replace('-', '_')] = v
            if v == "N/A":
                new_dic[k.replace('-', '_')] = "NA"
        return new_dic
