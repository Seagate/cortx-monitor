# Do NOT modify or remove this copyright and confidentiality notice

# Copyright 2017 Seagate Technology LLC or one of its affiliates.
#
# The code contained herein is CONFIDENTIAL to Seagate Technology LLC.
# Portions may also be trade secret. Any use, duplication, derivation,
# distribution or disclosure of this code, for any reason, not expressly
# authorized in writing by Seagate Technology LLC is prohibited.
# All rights are expressly reserved by Seagate Technology LLC.
# __author__ = 'Bhupesh Pant'

import plex.core.log as plex_log
from sspl_hl.utils.command_executor import RootCommandExecutor
from sspl_hl.utils.common import Components


class AccessPermission(object):
    """It will handle the backend work required to give the user
     access to the requested component.
    """

    def __init__(self, component, logger=plex_log):
        self.component = component
        self.logger = logger

    @staticmethod
    def get_object(component):
        """Creates and returns the ConfigureUser object based
         on the component type.
         """
        if component in [Components.SEASTREAM, Components.FS_CLI]:
            return AccessPermission(component)
        elif component in [Components.S3]:
            return S3AccessPermission()
        elif component in [Components.APACHE, Components.ROOT]:
            return WheelAccessPermission(component)
        elif component in [Components.RAS, Components.FS_GUI]:
            return AccessPermission(component)
        else:
            return AccessPermission(component)

    def grant_permission(self, user):
        """"Configure User as per the request."""
        GRANT_PERM_CMD = 'usermod {} -aG {}'
        perm_cmd = GRANT_PERM_CMD.format(user.username, self.component)
        cmd = RootCommandExecutor(perm_cmd)
        try:
            ret = cmd.run()
            return dict(ret_code=ret.get('ret_code'), output=ret.get('output'))
        except Exception as err:
            self.logger.warning('Access Permission for User: {}, '
                                'Component: {} Failed. Details: {}'
                                .format(user.username, str(err)))
            return dict(ret_code=1, output=str(err))


class WheelAccessPermission(AccessPermission):
    """Handles the backend work required to give the user
    access to sudo interface.
    """

    def __init__(self, component):
        super(WheelAccessPermission, self).__init__(component)

    def grant_permission(self, user):
        """Configure the user to wheel group. This includes adding
         the user to component group and then the wheel group.
        """
        ret = super(WheelAccessPermission, self).grant_permission(user)
        if ret.get('ret_code') > 0:
            return ret

        GRANT_PERM_CMD = 'usermod {} -aG wheel'
        perm_cmd = GRANT_PERM_CMD.format(user.username)
        cmd = RootCommandExecutor(perm_cmd)
        try:
            ret = cmd.run()
            return dict(ret_code=ret.get('ret_code'),
                        output=ret.get('output'))
        except Exception as err:
            self.logger.warning('Access Permission for User: {}, '
                                'Wheel Group: {} Failed. Details: {}'
                                .format(user.username, str(err)))
            return dict(ret_code=1, output=str(err))


class S3AccessPermission(AccessPermission):
    """Handles the backend work required to give the user
    access to S3admin interface
    """

    def __init__(self, component='s3'):
        super(S3AccessPermission, self).__init__(component)

    def grant_permission(self, user):
        """Configuring a user for s3 would be 2 step process,
        1. Create a default, S3 account
        2. Create a new S3 user linked with the above account.
        """
        pass


class RasAccessPermission(AccessPermission):
    """Handles the backend work required to give the user
    access to S3admin interface
    """

    def __init__(self, component='s3'):
        super(RasAccessPermission, self).__init__(component)

    def grant_permission(self, user):
        """Configuring a user for RAS
        """
        pass
