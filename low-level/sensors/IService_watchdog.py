"""
 ****************************************************************************
 Filename:          IService_watchdog.py
 Description:       Interface for all service watchdog classes
 Creation Date:     04/25/2015
 Author:            Jake Abernathy

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from zope.interface import Interface

class IServiceWatchdog(Interface):
    """Interface for service watchdog classes"""


    def read_data(self):
        """Notifies service to send its data"""
