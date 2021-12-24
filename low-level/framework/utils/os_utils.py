# Copyright (c) 2019-2020 Seagate Technology LLC and/or its Affiliates
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

"""
 ****************************************************************************
  Description:       Utility functions related to OS
 ****************************************************************************
"""

import socket

from cortx.utils.process import SimpleProcess, PipedProcess
from framework.base import sspl_constants as const


class OSUtils:
    """Base class for OS related utility functions."""

    @staticmethod
    def get_fqdn():
        """Get fully qualified domain name for current node."""
        return socket.getfqdn()

    @staticmethod
    def get_host_type():
        """
        Determine and get host hba type using lspci.

        Returns:
            scsi_host or fc_host if HBA card is installed
            Otherwise None.
        """
        host_type = ""

        # Check for fc host
        fc_host_check_cmd = "lspci | grep -Ei 'Fibre Channel'"
        _, _, rc = PipedProcess(fc_host_check_cmd).run()
        if rc == 0:
            host_type = const.FC_HOST

        # check for scsi host
        sas_hba_check_cmd = "lspci | grep -Ei 'Serial Attached SCSI|SAS|LSI|SCSI storage controller'"
        _, _, rc = PipedProcess(sas_hba_check_cmd).run()
        if rc == 0:
            host_type = const.SCSI_HOST

        return host_type
