"""
 ****************************************************************************
 Filename:          Ipsu.py
 Description:       Interface for all PSU related classes.
 Creation Date:     06/24/2019
 Author:            Malhar Vora

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from zope.interface import Interface

class IPSUsensor(Interface):
    """Interface for PSU related classes"""


    def read_data(self):
        """Reads PSU Data from some source"""
