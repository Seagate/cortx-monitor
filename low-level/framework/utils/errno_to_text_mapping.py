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

    
def map_errno_to_text(err_no):
    """Convert numerical errno to its meaning."""
    try:
        err_info = os.strerror(err_no)
        return err_info
    except ValueError as err:
        raise Exception("map_errno_to_text, Unknown error number: %s" % err)
    except Exception as err:
        logger.error("map_errno_to_text errno to text mapping failed due to %s: %s " % err)
        return
