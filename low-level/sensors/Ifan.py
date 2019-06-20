"""
 ****************************************************************************
 Filename:          Ifan.py
 Description:       Interface for all FAN sensor classes
 Creation Date:     10/07/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from zope.interface import Interface

class IFANsensor(Interface):
    """Interface for all RAID based sensor classes"""


    def read_data(self):
        """Method to access current RAID sensor data"""
