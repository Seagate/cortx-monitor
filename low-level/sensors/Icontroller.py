"""
 ****************************************************************************
 Filename:          Icontroller.py
 Description:       Interface for all Controller related classes.
 Creation Date:     07/17/2019
 Author:            Satish Darade

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from zope.interface import Interface

class IControllersensor(Interface):
    """Interface for Controller related classes"""


    def read_data(self):
        """Reads Controller Data from some source"""
