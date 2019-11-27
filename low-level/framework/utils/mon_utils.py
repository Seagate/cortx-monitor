"""
 ****************************************************************************
 Filename:          mon_utils.py
 Description:       Common utility functions required for monitoring purpose
 Creation Date:     11/27/2019
 Author:            Madhura Mande

 Do NOT modify or remove this copyright and confidentiality notice!
 Copyright (c) 2001 - $Date: 2015/01/14 $ Seagate Technology, LLC.
 The code contained herein is CONFIDENTIAL to Seagate Technology, LLC.
 Portions are also trade secret. Any use, duplication, derivation, distribution
 or disclosure of this code, for any reason, not expressly authorized is
 prohibited. All other rights are expressly reserved by Seagate Technology, LLC.
 ****************************************************************************
"""

import uuid

def get_alert_id(epoch_time):
    """Returns alert id which is a combination of
           epoch_time and salt value
    """
    salt = str(uuid.uuid4().hex)
    alert_id = epoch_time + salt
    return alert_id
