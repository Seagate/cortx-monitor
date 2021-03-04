# Copyright (c) 2020 Seagate Technology LLC and/or its Affiliates
#
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU Affero General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
# PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License along
# with this program. If not, see <https://www.gnu.org/licenses/>. For any questions
# about this software or licensing, please email opensource@seagate.com or
# cortx-questions@seagate.com.

import os
from framework.utils.service_logging import logger

class ErrnoMapping(object):

    def __init__(self):
        super(ErrnoMapping, self).__init__()
    
    def map_errno_to_text(self, err_no):
        """Convert numerical errno to its meaning."""
        try:
            err_info = os.strerror(err_no)
            return err_info
        except ValueError as e:
            raise Exception('ErrnoMapping, map_errno_to_text, Unknown error number: %s' % e)
            return
        except Exception as e:
            logger.error('ErrnoMapping, map_errno_to_text, Exception occured \
                            while mapping errno to text: %s ' % e)
            return