# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# __author__ = 'Bhupesh Pant'


class User(object):
    """Implementation of the user interface"""

    def __init__(self, username, pwd, authorizations=list()):
        self.username = username
        self.pwd = pwd
        self.authorizations = authorizations

    def __str__(self):
        """strigyfying the user object for pretty printing in JSON format
        NOTE: passwords will not be revealed out."""
        return dict(
            username=self.username,
            authorizations=self.authorizations
        ).__str__()
