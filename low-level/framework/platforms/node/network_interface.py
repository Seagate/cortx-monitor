# CORTX Python common library.
# Copyright (c) 2021 Seagate Technology LLC and/or its Affiliates
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
# For any questions about this software or licensing,
# please email opensource@seagate.com or cortx-questions@seagate.com

import os

from framework.utils.conf_utils import (
    Conf, SSPL_CONF, SYSFS_PATH, SYSTEM_INFORMATION)


class NetworkInterface:
    """The Class provides the access the Network interface information."""

    name = "NetworkInterface"

    def __init__(self):
        """Initialize the class"""
        sysfs_dir = Conf.get(SSPL_CONF,
                             f'{SYSTEM_INFORMATION}>{SYSFS_PATH}')
        self.base_dir = os.path.join(sysfs_dir, 'class', 'net')

    def get_link_state(self, interface):
        """
        Return the current physical link state of the interface.

            Posssible values are:
            1. DOWN  => physical link is down
            2. UP    => physical link is up
            3. UNKNOWN
        """
        link_status = {'0': 'DOWN', '1': 'UP'}
        carrier_file_path = os.path.join(self.base_dir, interface, 'carrier')

        try:
            with open(carrier_file_path) as cFile:
                carrier_indicator = cFile.read().strip()

            if carrier_indicator not in link_status:
                carrier_file_path = "UNKNOWN"
        except OSError as err:
            err_no, err_msg = err.args
            raise NetworkInterfaceError(err_no, (
                "Failed to read link state for interface '%s'"
                "due to error '%s'"), interface, err_msg)

        return link_status[carrier_indicator]

    def get_operational_state(self, interface):
        """
        Return the interface RFC2863 operational state as a string.

            Possible values are:
            1.'UNKNOWN' |  2.'NOTPRESENT" |  3.'DOWN' | 4.'LOWERLAYERDOWN'
            5.'TESTING' |  6.'DORMANT'    |  7.'UP'
        """
        operstate_file_path = os.path.join(self.base_dir,
                                           interface, 'operstate')
        operstates = ["UNKNOWN", "NOTPRESENT", "DOWN", "LOWERLAYERDOWN",
                      "TESTING", "DORMANT", "UP"]
        try:
            with open(operstate_file_path) as cFile:
                operstate = cFile.read().strip().upper()
            if operstate not in operstates:
                operstate = "UNKNOWN"
        except OSError as err:
            err_no, err_msg = err.args
            raise NetworkInterfaceError(err_no, (
                "Failed to read the operational state for ",
                "interface '%s'\n error Msg: %s"), interface, err_msg)
        return operstate


class NetworkInterfaceError(Exception):
    """Error Handling for Network Interface Operations."""

    def __init__(self, rc, message, *args):
        """Initialize the error information."""
        self._rc = rc
        self._desc = message % (args)

    @property
    def rc(self):
        return self._rc

    @property
    def desc(self):
        return self._desc

    def __str__(self):
        if self._rc == 0: return self._desc
        return "error(%d): %s" % (self._rc, self._desc)
