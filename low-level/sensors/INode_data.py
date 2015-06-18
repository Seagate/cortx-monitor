"""
 ****************************************************************************
 Filename:          INode_data.py
 Description:       Interface for all node data classes
 Creation Date:     06/10/2015
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

class INodeData(Interface):
    """Interface for node data classes"""


    def read_data(self, subset="All", debug=False):
        """Notifies module to return data based on a subset"""
