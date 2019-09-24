"""
 ****************************************************************************
 Filename:          INode_hw.py
 Description:       Interface for node hw class.
 Creation Date:     11/04/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2019/04/11 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

from zope.interface import Interface

class INodeHWsensor(Interface):
    """Interface for node hw class"""


    def read_data(self, subset="All", debug=False):
        """Notifies module to return data based on a subset"""
