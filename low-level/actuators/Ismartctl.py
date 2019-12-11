"""
 ****************************************************************************
 Filename:          Ismartctl.py
 Description:       Interface for all actuator based classes which uses smartctl tool to retrieve drive serial number
 Creation Date:     16/03/2019
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


class ISmartctl(Interface):
    """Interface for all actuator based classes using smartctl tool"""

    def perform_request(self, json_msg):
        """Notifies smart actuator to execute the desired command"""
