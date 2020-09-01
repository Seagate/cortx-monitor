#!/usr/bin/env python

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

from time import sleep
from subprocess import call

def create_nw_interface():
    # Load the dummy interface module
    call("modprobe dummy".split())
    sleep(.1)
    # Create a dummy interface called dummy1
    call("ip link set name eth-mocked dev dummy0".split())
    sleep(.1)
    call("ip link add eth-mocked type dummy".split())

def shuffle_nw_interface():
    create_nw_interface()
    sleep(.2)
    # Change interface's state from up/down to down/up
    call("ip link set eth-mocked up".split())
    sleep(2)
    call("ip link set eth-mocked down".split())
    sleep(.2)

def delete_nw_interface():
    call("ip link delete eth-mocked".split())